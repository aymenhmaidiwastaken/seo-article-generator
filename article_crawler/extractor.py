"""Article content extraction using trafilatura with relevance filtering."""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, List
from urllib.parse import urlparse

import requests
import trafilatura
from trafilatura.settings import use_config

from .utils import get_request_headers, random_delay

logger = logging.getLogger("article_crawler")

# Configure trafilatura for thorough extraction
TRAF_CONFIG = use_config()
TRAF_CONFIG.set("DEFAULT", "MIN_OUTPUT_SIZE", "200")
TRAF_CONFIG.set("DEFAULT", "MIN_EXTRACTED_SIZE", "200")


@dataclass
class ArticleData:
    """Container for extracted article data."""
    url: str
    title: str = ""
    content: str = ""
    author: str = ""
    date: str = ""
    meta_description: str = ""
    headings: List[str] = field(default_factory=list)
    word_count: int = 0
    keywords_found: List[str] = field(default_factory=list)
    source_domain: str = ""
    relevance_score: float = 0.0
    # Rewrite fields (filled later)
    rewritten_title: str = ""
    rewritten_content: str = ""
    rewrite_status: str = "pending"
    slug: str = ""
    category: str = ""


# Patterns that indicate junk/irrelevant content from Reddit etc.
JUNK_TITLE_PATTERNS = [
    r"^parking tips for",
    r"^\[for hire\]",
    r"^\[For Hire\]",
    r"^AITA\b",
    r"^AITAH\b",
    r"^TIFU\b",
    r"^My \(\d+[MF]\)",
    r"^I \(\d+[MF]\)",
    r"^Me \[\d+[MF]\]",
    r"CMV:",
    r"^LPT:",
    r"^YSK:",
    r"^TIL\b",
    r"^ELI5\b",
    r"^MEGATHREAD",
    r"\bAMA\b$",
    r"^r/\w+\s*-\s*Welcome Back",
    r"^Reddit\s*$",
    r"^Full coverage\s*$",
    r"^Articles\s*$",
    r"- Apps on Google Play$",
    r"- App Store$",
]

# Domains that usually contain junk, not real articles
JUNK_DOMAINS = {
    "old.reddit.com",
    "np.reddit.com",
    "i.reddit.com",
    "preview.redd.it",
    "v.redd.it",
    "i.redd.it",
    "play.google.com",
    "apps.apple.com",
}

# Common suffixes found after separators in titles (website/brand names)
# These get stripped: "Title | Smashing Magazine" → "Title"
TITLE_SEPARATOR_PATTERN = re.compile(
    r"\s*[\|–—―‐]\s*[^|–—―‐]{2,50}$"
)

# More aggressive: also catch " - Site Name" at end of title
TITLE_DASH_SUFFIX = re.compile(
    r"\s+-\s+(?:[A-Z][a-zA-Z\s&.']+(?:Blog|Magazine|News|Media|Inc|LLC|Ltd|Co|"
    r"\.com|\.io|\.org|\.net|Weekly|Daily|Times|Post|Wire|Hub|Docs|"
    r"Documentation|Developers|for Business|Studio|Software|Solutions|"
    r"Company|Agency|Services|Resources|Central|Guide|Academy|University|"
    r"Institute|Research|Labs|Tech|Digital|Group|Network|Partners|World|"
    r"Review|Insider|Journal|Gazette|Report|Forum|Community|Official|"
    r"Authority|Express|Platform|Experts?|Cloud|Apps?|Site|Online|"
    r"International|Global|Starters)?)$"
)

# Patterns for prefix branding: "Site Name: Actual Title" or "Site Name - Actual Title"
TITLE_PREFIX_BRAND = re.compile(
    r"^(?:[A-Z][a-zA-Z\s&.']{2,30}(?:Blog|Magazine|News|\.com|\.io))(?:\s*[:]\s*)"
)


def clean_title(title: str) -> str:
    """Remove website names, branding, and suffixes from article titles."""
    if not title:
        return title

    original = title

    # Step 1: Remove common separator-based suffixes
    # "Article Title | Website Name" → "Article Title"
    # "Article Title – TechCrunch" → "Article Title"
    # "Article Title — Smashing Magazine" → "Article Title"
    title = TITLE_SEPARATOR_PATTERN.sub("", title)

    # Step 2: Remove " - Site Name" suffix (only when it looks like a brand)
    title = TITLE_DASH_SUFFIX.sub("", title)

    # Step 3: Remove "Site Name: " prefix
    title = TITLE_PREFIX_BRAND.sub("", title)

    # Step 4: Remove common boilerplate suffixes not caught above
    boilerplate_suffixes = [
        " | Quora for Business",
        " | Quora",
        " - Wikipedia",
        " - GeeksforGeeks",
        " - GeeksForGeeks",
        " | Built In",
        " | IBM",
        " | Microsoft Azure",
        " | Microsoft",
        " | Google Search Central",
        " | Android Developers",
        " | Google for Developers",
        " | Kotlin Multiplatform",
        " | Codecademy",
        " - TechTarget Definition",
        " - TechTarget",
        " | TechCrunch",
        " | Similarweb",
        " | Fullstory",
        " - IGN",
        " | EPAM",
        " | RapidNative",
        " | Bubble Docs",
        " | Power Apps",
        " | App Maker",
        " | Jalasoft",
        " | Byteridge",
        " | Definition from TechTarget",
        " | Quora for Business",
    ]
    for suffix in boilerplate_suffixes:
        if title.endswith(suffix):
            title = title[: -len(suffix)]

    # Step 5: Remove trailing " (book)" or similar
    title = re.sub(r"\s*\(book\)\s*$", "", title, flags=re.IGNORECASE)

    # Clean up whitespace
    title = title.strip().strip("-–—|:").strip()

    # If we stripped too much, fall back to original
    if len(title) < 10:
        title = original

    return title


def normalize_for_dedup(title: str) -> str:
    """Normalize a title for deduplication comparison."""
    t = title.lower()
    # Remove all non-alphanumeric characters
    t = re.sub(r"[^a-z0-9\s]", "", t)
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    # Remove common filler words for better fuzzy matching
    for word in ["the", "a", "an", "in", "of", "for", "to", "and", "is", "on", "with"]:
        t = re.sub(rf"\b{word}\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def content_fingerprint(content: str) -> str:
    """Create a fingerprint from the first 200 words for dedup."""
    words = content.lower().split()[:200]
    return " ".join(words)


class ArticleExtractor:
    """Extracts article content from URLs using trafilatura with relevance filtering."""

    def __init__(
        self,
        min_word_count: int = 300,
        target_keywords: List[str] = None,
        min_relevance: float = 0.1,
        skip_dedup: bool = False,
    ):
        self.min_word_count = min_word_count
        self.target_keywords = [kw.lower() for kw in (target_keywords or [])]
        # Also split multi-word keywords into individual terms for partial matching
        self.keyword_terms = set()
        for kw in self.target_keywords:
            self.keyword_terms.update(kw.split())
        self.min_relevance = min_relevance
        self.skip_dedup = skip_dedup
        self.session = requests.Session()

        # Deduplication state
        self._seen_titles = set()
        self._seen_fingerprints = set()

        # Statistics tracking
        self.stats = {
            "total_processed": 0,
            "success": 0,
            "http_error": 0,
            "page_too_small": 0,
            "no_content": 0,
            "too_short": 0,
            "junk_title": 0,
            "low_relevance": 0,
            "duplicate_title": 0,
            "duplicate_content": 0,
            "junk_domain": 0,
            "timeout": 0,
            "connection_error": 0,
            "other_error": 0,
        }

    def extract(self, url: str) -> Optional[ArticleData]:
        """Extract article content from a URL. Returns None if fails, too short, irrelevant, or duplicate."""
        self.stats["total_processed"] += 1

        # Pre-filter junk domains
        domain = urlparse(url).netloc.lower()
        if domain in JUNK_DOMAINS:
            self.stats["junk_domain"] += 1
            return None

        try:
            self.session.headers.update(get_request_headers())
            resp = self.session.get(url, timeout=20, allow_redirects=True)

            if resp.status_code != 200:
                logger.debug(f"HTTP {resp.status_code} for {url}")
                self.stats["http_error"] += 1
                return None

            html = resp.text

            if not html or len(html) < 500:
                logger.debug(f"Page too small: {url}")
                self.stats["page_too_small"] += 1
                return None

            # Get clean text content
            content = trafilatura.extract(
                html,
                output_format="txt",
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=False,
                favor_recall=True,
                config=TRAF_CONFIG,
                url=url,
            )

            if not content:
                logger.debug(f"No text content for {url}")
                self.stats["no_content"] += 1
                return None

            # Word count check
            word_count = len(content.split())
            if word_count < self.min_word_count:
                logger.debug(f"Too short ({word_count} words): {url}")
                self.stats["too_short"] += 1
                return None

            # Extract metadata
            meta_obj = trafilatura.metadata.extract_metadata(html, url)

            title = ""
            author = ""
            date = ""
            description = ""

            if meta_obj:
                title = meta_obj.title or ""
                author = meta_obj.author or ""
                date = meta_obj.date or ""
                description = meta_obj.description or ""

            if not title:
                title = self._extract_title_fallback(html)

            # Clean the title: remove website names, branding, etc.
            title = clean_title(title)

            # Check for junk titles
            if self._is_junk_title(title):
                logger.debug(f"Junk title filtered: '{title}'")
                self.stats["junk_title"] += 1
                return None

            # Relevance check - must actually relate to our keywords
            relevance = self._compute_relevance(title, content)
            if relevance < self.min_relevance:
                logger.debug(f"Low relevance ({relevance:.2f}): '{title}'")
                self.stats["low_relevance"] += 1
                return None

            # Deduplication (can be disabled)
            if not self.skip_dedup:
                # Check title similarity
                norm_title = normalize_for_dedup(title)
                if norm_title in self._seen_titles:
                    logger.debug(f"Duplicate title: '{title}'")
                    self.stats["duplicate_title"] += 1
                    return None

                # Check content similarity (first 200 words)
                fp = content_fingerprint(content)
                if fp in self._seen_fingerprints:
                    logger.debug(f"Duplicate content: '{title}'")
                    self.stats["duplicate_content"] += 1
                    return None

                # Register for dedup
                self._seen_titles.add(norm_title)
                self._seen_fingerprints.add(fp)

            headings = self._extract_headings(html)
            keywords_found = self._find_keywords(content)
            source_domain = urlparse(url).netloc

            article = ArticleData(
                url=url,
                title=title,
                content=content,
                author=author,
                date=date,
                meta_description=description,
                headings=headings,
                word_count=word_count,
                keywords_found=keywords_found,
                source_domain=source_domain,
                relevance_score=relevance,
            )

            self.stats["success"] += 1
            logger.debug(
                f"Extracted: '{title}' ({word_count} words, rel={relevance:.2f}) "
                f"from {source_domain}"
            )
            return article

        except requests.exceptions.Timeout:
            logger.debug(f"Timeout: {url}")
            self.stats["timeout"] += 1
            return None
        except requests.exceptions.ConnectionError:
            logger.debug(f"Connection error: {url}")
            self.stats["connection_error"] += 1
            return None
        except Exception as e:
            logger.debug(f"Extraction error for {url}: {e}")
            self.stats["other_error"] += 1
            return None

    def print_stats(self):
        """Print extraction statistics."""
        total = self.stats["total_processed"]
        if total == 0:
            return
        print("\n  Extraction Statistics:")
        print(f"    Total URLs processed:  {total}")
        print(f"    Successful:            {self.stats['success']} ({100*self.stats['success']/total:.1f}%)")
        print(f"    HTTP errors:           {self.stats['http_error']}")
        print(f"    Timeouts:              {self.stats['timeout']}")
        print(f"    Connection errors:     {self.stats['connection_error']}")
        print(f"    No content extracted:  {self.stats['no_content']}")
        print(f"    Too short:             {self.stats['too_short']}")
        print(f"    Low relevance:         {self.stats['low_relevance']}")
        print(f"    Junk titles:           {self.stats['junk_title']}")
        print(f"    Junk domains:          {self.stats['junk_domain']}")
        print(f"    Duplicate titles:      {self.stats['duplicate_title']}")
        print(f"    Duplicate content:     {self.stats['duplicate_content']}")

    def _is_junk_title(self, title: str) -> bool:
        """Check if the title matches known junk patterns."""
        for pattern in JUNK_TITLE_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        # Too short or generic
        if len(title.strip()) < 10:
            return True
        return False

    def _compute_relevance(self, title: str, content: str) -> float:
        """Compute a relevance score (0-1) based on keyword presence.

        Uses a flexible scoring system based on individual keyword terms,
        with bonuses for full phrase matches.
        """
        if not self.target_keywords:
            return 1.0

        title_lower = title.lower()
        content_sample = content[:3000].lower()
        text = f"{title_lower} {title_lower} {content_sample}"

        total_terms = len(self.keyword_terms)
        if total_terms == 0:
            return 1.0

        # Count individual keyword terms present (this is the main score now)
        terms_found = sum(1 for term in self.keyword_terms if term in text)

        # Must have at least 2 keyword terms (e.g., "mobile" and "app" or "ai" and "game")
        if terms_found < 2:
            return 0.0

        # Base score from individual terms (0 to 0.6)
        term_score = min(terms_found / total_terms, 1.0) * 0.6

        # Count full phrase matches for bonus points
        phrase_in_title = sum(1 for kw in self.target_keywords if kw in title_lower)
        phrase_in_content = sum(1 for kw in self.target_keywords if kw in content_sample)

        # Bonus for phrase matches (0 to 0.4)
        title_bonus = min(phrase_in_title, 3) * 0.1
        content_bonus = min(phrase_in_content, 3) * 0.03

        score = term_score + title_bonus + content_bonus
        return min(score, 1.0)

    def _extract_title_fallback(self, html: str) -> str:
        """Fallback title extraction from HTML."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Prefer og:title (usually cleaner than <title>)
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return og["content"].strip()

        # Try h1 (usually the article title without site branding)
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            if len(text) > 10:
                return text

        # Fall back to <title> tag
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        return "Untitled"

    def _extract_headings(self, html: str) -> List[str]:
        """Extract H1-H3 headings from HTML."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        headings = []

        for tag in soup.find_all(re.compile(r"^h[1-3]$")):
            text = tag.get_text(strip=True)
            if text:
                level = tag.name
                headings.append(f"[{level.upper()}] {text}")

        return headings

    def _find_keywords(self, content: str) -> List[str]:
        """Find which target keywords appear in the content."""
        content_lower = content.lower()
        found = []
        for kw in self.target_keywords:
            if kw in content_lower:
                found.append(kw)
        return found

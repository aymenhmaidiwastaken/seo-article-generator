"""Utility functions: user agents, delays, slug generation, logging."""

import logging
import random
import re
import time
import unicodedata
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_request_headers() -> dict:
    return {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication."""
    parsed = urlparse(url)
    # Remove common tracking parameters
    tracking_params = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
    }
    query = parse_qs(parsed.query)
    filtered = {k: v for k, v in query.items() if k not in tracking_params}
    clean_query = urlencode(filtered, doseq=True)
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower().rstrip("."),
        parsed.path.rstrip("/"),
        parsed.params,
        clean_query,
        "",  # remove fragment
    ))
    return normalized


def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    slug = unicodedata.normalize("NFKD", title)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = slug.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    # Limit length
    if len(slug) > 80:
        slug = slug[:80].rsplit("-", 1)[0]
    return slug


def is_valid_article_url(url: str) -> bool:
    """Filter out URLs that are unlikely to be articles."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    # Skip non-HTTP
    if parsed.scheme not in ("http", "https"):
        return False

    # Skip file downloads
    skip_extensions = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".rar", ".tar", ".gz", ".exe", ".dmg", ".iso",
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".mp4",
        ".mp3", ".avi", ".mov",
    }
    for ext in skip_extensions:
        if path.endswith(ext):
            return False

    # Skip social media profiles/homepages (not article pages)
    skip_patterns = [
        r"^/$",  # homepage only
        r"/login", r"/signup", r"/register", r"/cart", r"/checkout",
        r"/account", r"/settings", r"/privacy", r"/terms",
    ]
    for pattern in skip_patterns:
        if re.search(pattern, path):
            return False

    # Skip known non-article domains
    skip_domains = {
        "youtube.com", "www.youtube.com", "twitter.com", "x.com",
        "facebook.com", "www.facebook.com", "instagram.com",
        "tiktok.com", "pinterest.com", "linkedin.com",
    }
    if domain in skip_domains:
        return False

    return True


def setup_logging(verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("article_crawler")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if not logger.handlers:
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG if verbose else logging.INFO)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(message)s",
            datefmt="%H:%M:%S",
        )
        console.setFormatter(fmt)
        logger.addHandler(console)

        file_handler = logging.FileHandler("crawler.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        ))
        logger.addHandler(file_handler)

    return logger

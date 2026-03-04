"""SEO-optimized article rewriting using Ollama (local LLM)."""

import logging
import re
import time
from typing import Optional

import requests

from .extractor import ArticleData
from .utils import generate_slug

logger = logging.getLogger("article_crawler")

# Two-step approach: Step 1 rewrites content, Step 2 extracts metadata
# This is far more reliable than asking for JSON in one shot

REWRITE_PROMPT = """Rewrite the following article to be completely unique. Rephrase every sentence. Keep the same information. Write in an engaging, SEO-friendly tone. Use the target keyword naturally 3-5 times. Structure with ## headings and short paragraphs.

TARGET KEYWORD: {keyword}
ORIGINAL TITLE: {title}

ARTICLE:
{content}

Now write the rewritten article below. Start with a new SEO title on the first line, then a blank line, then the full rewritten article:"""

META_PROMPT = """Given this article title, write a 150-character SEO meta description and pick ONE category from this list: Technology, Health, Finance, Lifestyle, Business, Education, Travel, Food, Sports, Entertainment, Science, Other

TITLE: {title}

Reply with exactly two lines:
META: your meta description here
CATEGORY: category name here"""

MAX_RETRIES = 3
RETRY_DELAY = 5


class OllamaRewriter:
    """Rewrites articles using a local Ollama LLM instance."""

    def __init__(
        self,
        model: str = "llama3",
        ollama_url: str = "http://localhost:11434",
        target_keyword: str = "",
    ):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.target_keyword = target_keyword
        self._check_connection()

    def _check_connection(self):
        """Verify Ollama is running and the model is available."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                logger.warning(f"Ollama returned HTTP {resp.status_code}")
                return

            models = resp.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]

            if self.model not in model_names:
                available = ", ".join(model_names) if model_names else "none"
                logger.warning(
                    f"Model '{self.model}' not found in Ollama. "
                    f"Available: {available}. "
                    f"Run: ollama pull {self.model}"
                )
            else:
                logger.info(f"Ollama connected: model '{self.model}' ready")

        except requests.exceptions.ConnectionError:
            logger.error(
                "Cannot connect to Ollama. Make sure it's running: "
                "https://ollama.ai/download"
            )
        except Exception as e:
            logger.error(f"Ollama check failed: {e}")

    def _call_ollama(self, prompt: str, max_tokens: int = 4096) -> Optional[str]:
        """Call Ollama with retry logic."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "num_predict": max_tokens,
                        },
                    },
                    timeout=300,
                )

                if resp.status_code != 200:
                    logger.warning(f"Ollama HTTP {resp.status_code} (attempt {attempt}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
                        continue
                    return None

                result = resp.json()
                return result.get("response", "")

            except requests.exceptions.Timeout:
                logger.warning(f"Ollama timeout (attempt {attempt}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
            except requests.exceptions.ConnectionError:
                logger.warning(f"Ollama connection error (attempt {attempt}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * 2)
            except Exception as e:
                logger.error(f"Ollama error: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)

        return None

    def rewrite(self, article: ArticleData) -> ArticleData:
        """Rewrite an article using Ollama. Returns the modified article."""
        # Truncate very long articles to fit in context window
        content = article.content
        if len(content) > 6000:
            content = content[:6000]

        # Step 1: Rewrite the article
        prompt = REWRITE_PROMPT.format(
            keyword=self.target_keyword or "the topic",
            title=article.title,
            content=content,
        )

        response = self._call_ollama(prompt, max_tokens=4096)

        if not response or len(response.strip()) < 100:
            logger.warning(f"Empty/short rewrite for: '{article.title}'")
            article.rewrite_status = "failed"
            return article

        # Parse the response: first line = title, rest = content
        lines = response.strip().split("\n", 1)
        rewritten_title = lines[0].strip()
        rewritten_content = lines[1].strip() if len(lines) > 1 else response.strip()

        # Clean up the title (remove markdown, quotes, prefixes)
        rewritten_title = re.sub(r'^[#*"\'\s]+', "", rewritten_title)
        rewritten_title = re.sub(r'["\'\s]+$', "", rewritten_title)
        # Remove common LLM prefixes
        for prefix in ["Title:", "New Title:", "Rewritten Title:", "SEO Title:", "Here is"]:
            if rewritten_title.lower().startswith(prefix.lower()):
                rewritten_title = rewritten_title[len(prefix):].strip()
                rewritten_title = rewritten_title.lstrip(":").strip()

        if not rewritten_title or len(rewritten_title) < 10:
            rewritten_title = article.title

        article.rewritten_title = rewritten_title
        article.rewritten_content = rewritten_content
        article.slug = generate_slug(rewritten_title)

        # Step 2: Get meta description and category (quick call)
        meta_prompt = META_PROMPT.format(title=rewritten_title)
        meta_response = self._call_ollama(meta_prompt, max_tokens=200)

        if meta_response:
            self._parse_meta(meta_response, article)
        else:
            article.category = "Other"

        article.rewrite_status = "completed"
        logger.info(f"Rewritten: '{rewritten_title}'")
        return article

    def _parse_meta(self, text: str, article: ArticleData):
        """Parse META: and CATEGORY: lines from response."""
        valid_categories = {
            "technology", "health", "finance", "lifestyle", "business",
            "education", "travel", "food", "sports", "entertainment",
            "science", "other",
        }

        for line in text.strip().split("\n"):
            line = line.strip()
            if line.upper().startswith("META:"):
                desc = line[5:].strip()
                if len(desc) > 10:
                    article.meta_description = desc[:160]
            elif line.upper().startswith("CATEGORY:"):
                cat = line[9:].strip().title()
                if cat.lower() in valid_categories:
                    article.category = cat
                else:
                    article.category = "Other"

        if not article.category:
            article.category = "Other"

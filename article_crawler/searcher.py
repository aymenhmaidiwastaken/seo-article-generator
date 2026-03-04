"""Multi-engine search: Google, Bing, DuckDuckGo, Reddit, Quora."""

import logging
import re
import warnings
from typing import List, Set
from urllib.parse import quote_plus, urljoin, unquote

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

from .utils import (
    get_request_headers,
    normalize_url,
    is_valid_article_url,
    random_delay,
)

# Suppress noisy deprecation warnings from lxml/bs4
warnings.filterwarnings("ignore", category=DeprecationWarning, module="bs4")

logger = logging.getLogger("article_crawler")


class SearchEngine:
    """Base class for search engines."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(get_request_headers())

    def search(self, query: str, num_results: int = 100) -> List[str]:
        raise NotImplementedError


class DuckDuckGoSearcher(SearchEngine):
    """Search using DuckDuckGo (most reliable free option)."""

    def search(self, query: str, num_results: int = 100) -> List[str]:
        urls = []
        try:
            ddgs = DDGS()
            results = ddgs.text(
                query,
                region="us-en",
                safesearch="off",
                max_results=num_results,
            )
            for r in results:
                url = r.get("href", "") or r.get("url", "")
                if url and is_valid_article_url(url):
                    urls.append(url)
            logger.info(f"DuckDuckGo: found {len(urls)} URLs for '{query}'")
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
        return urls


class GoogleSearcher(SearchEngine):
    """Search Google via scraping."""

    def search(self, query: str, num_results: int = 100) -> List[str]:
        urls = []
        pages = min((num_results // 10) + 1, 5)  # Cap at 5 pages to avoid blocks

        for page in range(pages):
            if len(urls) >= num_results:
                break
            try:
                start = page * 10
                params = {
                    "q": query,
                    "start": start,
                    "num": 10,
                    "hl": "en",
                    "gl": "us",
                }
                self.session.headers.update(get_request_headers())
                resp = self.session.get(
                    "https://www.google.com/search",
                    params=params,
                    timeout=15,
                )

                if resp.status_code == 429:
                    logger.warning("Google: rate limited, stopping")
                    break
                if resp.status_code != 200:
                    logger.warning(f"Google: HTTP {resp.status_code}")
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                found_on_page = 0

                # Method 1: /url?q= links (classic Google)
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if "/url?q=" in href:
                        actual_url = href.split("/url?q=")[1].split("&")[0]
                        actual_url = unquote(actual_url)
                        if is_valid_article_url(actual_url):
                            urls.append(actual_url)
                            found_on_page += 1

                # Method 2: Direct links in search result divs
                if found_on_page == 0:
                    for div in soup.find_all("div", class_="g"):
                        a_tag = div.find("a", href=True)
                        if a_tag:
                            href = a_tag["href"]
                            if href.startswith("http") and "google.com" not in href:
                                if is_valid_article_url(href):
                                    urls.append(href)
                                    found_on_page += 1

                # Method 3: Any external link not from Google
                if found_on_page == 0:
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"]
                        if href.startswith("http") and "google" not in href.lower():
                            if is_valid_article_url(href):
                                urls.append(href)
                                found_on_page += 1

                if found_on_page == 0:
                    logger.debug(f"Google page {page}: no results found, may be blocked")
                    break

                random_delay(3.0, 6.0)

            except Exception as e:
                logger.error(f"Google search page {page} failed: {e}")
                break

        logger.info(f"Google: found {len(urls)} URLs for '{query}'")
        return urls


class BingSearcher(SearchEngine):
    """Search Bing via scraping."""

    def search(self, query: str, num_results: int = 100) -> List[str]:
        urls = []
        pages = min((num_results // 10) + 1, 5)

        for page in range(pages):
            if len(urls) >= num_results:
                break
            try:
                first = page * 10 + 1
                params = {
                    "q": query,
                    "first": first,
                    "count": 10,
                    "setlang": "en",
                    "cc": "US",
                }
                self.session.headers.update(get_request_headers())
                resp = self.session.get(
                    "https://www.bing.com/search",
                    params=params,
                    timeout=15,
                )

                if resp.status_code != 200:
                    logger.warning(f"Bing: HTTP {resp.status_code}")
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                found_on_page = 0

                # Standard Bing result structure
                for li in soup.find_all("li", class_="b_algo"):
                    a_tag = li.find("a", href=True)
                    if a_tag:
                        href = a_tag["href"]
                        if href.startswith("http") and is_valid_article_url(href):
                            urls.append(href)
                            found_on_page += 1

                # Fallback: look for result links in other containers
                if found_on_page == 0:
                    for h2 in soup.find_all("h2"):
                        a_tag = h2.find("a", href=True)
                        if a_tag:
                            href = a_tag["href"]
                            if href.startswith("http") and "bing.com" not in href:
                                if is_valid_article_url(href):
                                    urls.append(href)
                                    found_on_page += 1

                if found_on_page == 0:
                    logger.debug(f"Bing page {page}: no results, stopping")
                    break

                random_delay(2.0, 5.0)

            except Exception as e:
                logger.error(f"Bing search page {page} failed: {e}")
                break

        logger.info(f"Bing: found {len(urls)} URLs for '{query}'")
        return urls


class RedditSearcher(SearchEngine):
    """Search Reddit for relevant posts/articles."""

    def search(self, query: str, num_results: int = 100) -> List[str]:
        urls = []
        try:
            self.session.headers.update(get_request_headers())
            params = {
                "q": query,
                "sort": "relevance",
                "t": "all",
                "type": "link",
                "limit": 100,
            }
            resp = self.session.get(
                "https://www.reddit.com/search.json",
                params=params,
                timeout=15,
            )

            if resp.status_code == 429:
                logger.warning("Reddit: rate limited")
                return urls
            if resp.status_code != 200:
                logger.warning(f"Reddit: HTTP {resp.status_code}")
                return urls

            data = resp.json()
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                post_data = post.get("data", {})
                url = post_data.get("url", "")
                if url and not url.startswith("https://www.reddit.com"):
                    if is_valid_article_url(url):
                        urls.append(url)

                # Skip Reddit self-posts - they're usually not articles
                # (relationship drama, memes, personal stories, spam)

            random_delay(1.0, 3.0)

        except Exception as e:
            logger.error(f"Reddit search failed: {e}")

        logger.info(f"Reddit: found {len(urls)} URLs for '{query}'")
        return urls


class QuoraSearcher(SearchEngine):
    """Search Quora via DuckDuckGo site-specific search."""

    def search(self, query: str, num_results: int = 50) -> List[str]:
        urls = []
        try:
            site_query = f"site:quora.com {query}"
            ddgs = DDGS()
            results = ddgs.text(
                site_query,
                region="us-en",
                safesearch="off",
                max_results=num_results,
            )
            for r in results:
                url = r.get("href", "") or r.get("url", "")
                if url and "quora.com" in url:
                    urls.append(url)
            logger.info(f"Quora: found {len(urls)} URLs for '{query}'")
        except Exception as e:
            logger.error(f"Quora search failed: {e}")
        return urls


class MultiSearcher:
    """Aggregates results from all search engines."""

    def __init__(self, engines: List[str] = None):
        available = {
            "duckduckgo": DuckDuckGoSearcher,
            "google": GoogleSearcher,
            "bing": BingSearcher,
            "reddit": RedditSearcher,
            "quora": QuoraSearcher,
        }
        if engines is None:
            engines = list(available.keys())

        self.searchers = {}
        for name in engines:
            name_lower = name.lower()
            if name_lower in available:
                self.searchers[name_lower] = available[name_lower]()
            else:
                logger.warning(f"Unknown search engine: {name}")

    def search(self, keywords: List[str], results_per_engine: int = 100) -> List[str]:
        """Search all engines for all keywords, return deduplicated URL list."""
        seen_normalized: Set[str] = set()
        unique_urls: List[str] = []

        for keyword in keywords:
            logger.info(f"Searching for: '{keyword}'")

            queries = self._build_query_variations(keyword)

            for engine_name, engine in self.searchers.items():
                for query in queries:
                    logger.debug(f"  {engine_name}: '{query}'")
                    try:
                        results = engine.search(query, num_results=results_per_engine)
                        new_count = 0
                        for url in results:
                            norm = normalize_url(url)
                            if norm not in seen_normalized:
                                seen_normalized.add(norm)
                                unique_urls.append(url)
                                new_count += 1
                        if new_count:
                            logger.info(f"  {engine_name} '{query}': +{new_count} new URLs")
                    except Exception as e:
                        logger.error(f"  {engine_name} failed for '{query}': {e}")

                    random_delay(1.0, 3.0)

        logger.info(f"Total unique URLs collected: {len(unique_urls)}")
        return unique_urls

    def _build_query_variations(self, keyword: str) -> List[str]:
        """Generate query variations for broader coverage."""
        return [
            keyword,
            f"{keyword} guide",
            f"{keyword} tutorial",
            f"{keyword} tips",
            f"{keyword} how to",
            f"{keyword} best practices",
            f"best {keyword}",
            f"top {keyword}",
            f"{keyword} 2025",
            f"{keyword} 2024",
            f"{keyword} trends",
            f"{keyword} examples",
            f"{keyword} for beginners",
            f"{keyword} explained",
            f"{keyword} strategies",
            f"{keyword} tools",
            f"{keyword} comparison",
            f"{keyword} review",
            f"{keyword} case study",
            f"{keyword} benefits",
            f"{keyword} vs",
            f"what is {keyword}",
            f"why {keyword}",
            f"{keyword} statistics",
            f"{keyword} future",
        ]

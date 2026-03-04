"""Checkpoint system for saving/resuming crawl progress."""

import json
import logging
import os
from dataclasses import asdict
from typing import Dict, List, Optional, Set

from .extractor import ArticleData

logger = logging.getLogger("article_crawler")


class CheckpointManager:
    """Saves and restores crawl progress to allow resuming interrupted jobs."""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)

    def _get_path(self, job_id: str) -> str:
        return os.path.join(self.checkpoint_dir, f"{job_id}.json")

    def save(
        self,
        job_id: str,
        keywords: List[str],
        all_urls: List[str],
        processed_urls: Set[str],
        articles: List[ArticleData],
        phase: str = "crawling",
        rewrite_index: int = 0,
    ):
        """Save current progress to checkpoint file."""
        data = {
            "job_id": job_id,
            "keywords": keywords,
            "phase": phase,
            "all_urls": all_urls,
            "processed_urls": list(processed_urls),
            "rewrite_index": rewrite_index,
            "articles": [self._article_to_dict(a) for a in articles],
            "stats": {
                "total_urls": len(all_urls),
                "processed": len(processed_urls),
                "extracted": len(articles),
                "rewritten": sum(
                    1 for a in articles if a.rewrite_status == "completed"
                ),
            },
        }

        path = self._get_path(job_id)
        temp_path = path + ".tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # Atomic rename
            if os.path.exists(path):
                os.remove(path)
            os.rename(temp_path, path)
            logger.debug(f"Checkpoint saved: {data['stats']}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def load(self, job_id: str) -> Optional[Dict]:
        """Load checkpoint data. Returns None if no checkpoint exists."""
        path = self._get_path(job_id)
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Rebuild ArticleData objects
            data["articles"] = [
                self._dict_to_article(d) for d in data.get("articles", [])
            ]
            data["processed_urls"] = set(data.get("processed_urls", []))

            logger.info(
                f"Checkpoint loaded: {data['stats']['processed']}/{data['stats']['total_urls']} "
                f"URLs processed, {data['stats']['extracted']} articles extracted"
            )
            return data

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def exists(self, job_id: str) -> bool:
        return os.path.exists(self._get_path(job_id))

    def delete(self, job_id: str):
        path = self._get_path(job_id)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Checkpoint deleted: {job_id}")

    def _article_to_dict(self, article: ArticleData) -> dict:
        return asdict(article)

    def _dict_to_article(self, d: dict) -> ArticleData:
        # Handle old checkpoints that may be missing newer fields
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(ArticleData)}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return ArticleData(**filtered)

    @staticmethod
    def generate_job_id(keywords: List[str]) -> str:
        """Generate a deterministic job ID from keywords."""
        import hashlib
        key = "_".join(sorted(kw.lower().strip() for kw in keywords))
        short_hash = hashlib.md5(key.encode()).hexdigest()[:8]
        # Use first keyword for readability
        safe_name = "".join(
            c if c.isalnum() else "_" for c in keywords[0].lower()
        )[:30]
        return f"{safe_name}_{short_hash}"

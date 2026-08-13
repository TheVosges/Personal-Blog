"""Storage layer for the Personal Blog application.

Handles filesystem-based CRUD operations for articles stored as JSON files.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def slugify(text: str) -> str:
    """Convert a title text into a clean URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "untitled-article"


def estimate_reading_time(content: str, words_per_minute: int = 200) -> int:
    """Calculate estimated reading time in minutes."""
    word_count = len(content.split())
    return max(1, round(word_count / words_per_minute))


class StorageManager:
    """Manages reading, writing, and deleting article files on the filesystem."""

    def __init__(self, storage_dir: Optional[str | Path] = None) -> None:
        if storage_dir is None:
            base_path = Path(__file__).resolve().parent
            self.storage_dir = base_path / "articles"
        else:
            self.storage_dir = Path(storage_dir)

        # Ensure articles directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, slug: str) -> Path:
        """Get the expected JSON file path for a given slug."""
        # Sanitize slug to prevent directory traversal
        clean_slug = os.path.basename(slug.strip())
        return self.storage_dir / f"{clean_slug}.json"

    def get_all_articles(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all articles, sorted by publication date descending."""
        articles: List[Dict[str, Any]] = []

        if not self.storage_dir.exists():
            return articles

        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # Ensure fallback fields
                        if "slug" not in data:
                            data["slug"] = file_path.stem
                        if "reading_time" not in data and "content" in data:
                            data["reading_time"] = estimate_reading_time(
                                data["content"]
                            )
                        articles.append(data)
            except (json.JSONDecodeError, OSError):
                # Ignore corrupt or unreadable files gracefully
                continue

        # Filter by tag if requested
        if tag:
            tag_clean = tag.strip().lower()
            articles = [
                a
                for a in articles
                if any(t.strip().lower() == tag_clean for t in a.get("tags", []))
            ]

        # Sort by date descending (fallback to empty string)
        articles.sort(key=lambda x: x.get("date", ""), reverse=True)
        return articles

    def get_article(self, slug: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single article by its slug."""
        file_path = self._get_file_path(slug)
        if not file_path.is_file():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("slug", slug)
                    if "content" in data:
                        data.setdefault(
                            "reading_time", estimate_reading_time(data["content"])
                        )
                    return data
        except (json.JSONDecodeError, OSError):
            return None
        return None

    def save_article(
        self,
        title: str,
        content: str,
        slug: Optional[str] = None,
        date: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        old_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a new or updated article to disk.

        Args:
            title: Title of the article.
            content: Main text content of the article.
            slug: Desired URL slug (generated from title if not provided).
            date: Publication date string (defaults to today's date YYYY-MM-DD).
            summary: Short description (auto-generated if omitted).
            tags: List of tag strings.
            old_slug: If updating an existing article with a changed slug.

        Returns:
            The saved article dictionary.
        """
        # Determine slug
        target_slug = slugify(slug) if slug else slugify(title)
        if not target_slug:
            target_slug = "article-" + datetime.now().strftime("%Y%m%d%H%M%S")

        # Determine date
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        # Determine summary
        if not summary:
            # Extract first ~160 chars or first line as summary
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            first_line = lines[0] if lines else ""
            summary = (
                (first_line[:157] + "...") if len(first_line) > 160 else first_line
            )

        # Clean tags
        clean_tags = [t.strip() for t in (tags or []) if t.strip()]

        article_data: Dict[str, Any] = {
            "title": title.strip(),
            "slug": target_slug,
            "date": date.strip(),
            "summary": summary.strip(),
            "content": content,
            "tags": clean_tags,
            "reading_time": estimate_reading_time(content),
            "updated_at": datetime.now().isoformat(),
        }

        # If slug changed or updating with old_slug, remove old file
        if old_slug and old_slug != target_slug:
            self.delete_article(old_slug)

        new_file_path = self._get_file_path(target_slug)
        with open(new_file_path, "w", encoding="utf-8") as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)

        return article_data

    def delete_article(self, slug: str) -> bool:
        """Delete an article file by its slug.

        Returns:
            True if file existed and was removed, False otherwise.
        """
        file_path = self._get_file_path(slug)
        if file_path.is_file():
            try:
                file_path.unlink()
                return True
            except OSError:
                return False
        return False

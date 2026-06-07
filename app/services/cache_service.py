"""Shared cache-backed services for UI state and path persistence."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.data.file_cache import FileCache


class CacheService:
    def __init__(self, file_cache: FileCache | None = None):
        self.file_cache = file_cache or FileCache()

    def fetch_kabutan_html_dir(self) -> Path | None:
        return self.file_cache.fetch_kabutan_html_dir_cache()

    def save_kabutan_html_dir(self, path: Path) -> None:
        self.file_cache.save_kabutan_html_dir_cache(path)

    def fetch_watchlist_path(self) -> Path | None:
        return self.file_cache.fetch_watchlist_path_cache()

    def save_watchlist_path(self, path: Path) -> None:
        self.file_cache.save_watchlist_path_cache(path)

    def fetch_output_cache_for_today(self, *, today: date | None = None) -> dict[str, str]:
        return self.file_cache.fetch_output_cache_for_today(today=today)

    def save_output_cache_for_today(self, output_cache: dict[str, str], *, today: date | None = None) -> None:
        self.file_cache.save_output_cache_for_today(output_cache, today=today)

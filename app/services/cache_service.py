"""Shared cache-backed services for UI state and path persistence."""

from __future__ import annotations

from pathlib import Path

from app.data.file_cache import FileCache


class CacheService:
    def __init__(self, file_cache: FileCache | None = None):
        self.file_cache = file_cache or FileCache()

    def fetch_kabutan_html_dir(self) -> Path | None:
        return self.file_cache.fetch_kabutan_html_dir_cache()

    def save_kabutan_html_dir(self, path: Path) -> None:
        self.file_cache.save_kabutan_html_dir_cache(path)

    def fetch_kabutan_package_zip(self) -> Path | None:
        return self.file_cache.fetch_kabutan_package_zip_cache()

    def save_kabutan_package_zip(self, path: Path) -> None:
        self.file_cache.save_kabutan_package_zip_cache(path)

    def clear_kabutan_package_zip(self) -> None:
        self.file_cache.clear_kabutan_package_zip_cache()

    def fetch_watchlist_path(self) -> Path | None:
        return self.file_cache.fetch_watchlist_path_cache()

    def save_watchlist_path(self, path: Path) -> None:
        self.file_cache.save_watchlist_path_cache(path)


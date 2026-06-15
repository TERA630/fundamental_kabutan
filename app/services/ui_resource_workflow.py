"""Workflow for UI-selected resource paths and caches."""

from __future__ import annotations

from pathlib import Path

from app.domain.usecases.kabutan_html_dir import ResolvedKabutanHtmlDir
from app.domain.usecases.watchlist_path import ResolveWatchlistPathUseCase, ResolvedWatchlistPath
from app.services.cache_service import CacheService
from app.services.kabutan_html_dir_service import KabutanHtmlDirService
from app.services.watchlist_service import WatchlistService


class UiResourceWorkflow:
    def __init__(
        self,
        *,
        cache_service: CacheService,
        watchlist_service: WatchlistService,
        kabutan_html_dir_service: KabutanHtmlDirService,
    ):
        self.cache_service = cache_service
        self.watchlist_service = watchlist_service
        self.kabutan_html_dir_service = kabutan_html_dir_service
        self.resolve_watchlist_path_usecase = ResolveWatchlistPathUseCase()

    def fetch_resolved_kabutan_html_dir(self) -> ResolvedKabutanHtmlDir:
        return self.kabutan_html_dir_service.resolve_cached_dir()

    def save_kabutan_html_dir_cache(self, path: Path) -> None:
        self.kabutan_html_dir_service.save_dir(path)

    def fetch_kabutan_package_zip_cache(self) -> Path | None:
        cached_path = self.cache_service.fetch_kabutan_package_zip()
        if cached_path is not None and cached_path.exists() and cached_path.is_file():
            return cached_path
        return None

    def save_kabutan_package_zip_cache(self, path: Path) -> None:
        self.cache_service.save_kabutan_package_zip(path)

    def clear_kabutan_package_zip_cache(self) -> None:
        self.cache_service.clear_kabutan_package_zip()

    def fetch_resolved_watchlist_path(self) -> ResolvedWatchlistPath:
        cached_path = self.watchlist_service.restore_watchlist_path()
        return self.resolve_watchlist_path_usecase.fetch_resolved_watchlist_path(cached_path)

    def save_watchlist_path_cache(self, path: Path) -> None:
        self.watchlist_service.save_watchlist_path(path)

    def fetch_watchlist_entries(self, path: Path) -> list[tuple[str, str]]:
        return self.watchlist_service.load_from_file(path)


__all__ = ["UiResourceWorkflow"]

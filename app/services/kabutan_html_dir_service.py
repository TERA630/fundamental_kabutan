"""Kabutan HTML directory resolution and persistence service."""

from __future__ import annotations

from pathlib import Path

from app.domain.usecases.kabutan_html_dir import ResolveKabutanHtmlDirUseCase, ResolvedKabutanHtmlDir
from app.services.cache_service import CacheService


class KabutanHtmlDirService:
    def __init__(self, cache_service: CacheService | None = None):
        self.cache_service = cache_service or CacheService()
        self.resolve_usecase = ResolveKabutanHtmlDirUseCase()

    def resolve_cached_dir(self) -> ResolvedKabutanHtmlDir:
        cached_dir = self.cache_service.fetch_kabutan_html_dir()
        return self.resolve_usecase.fetch_resolved_kabutan_html_dir(cached_dir)

    def save_dir(self, path: Path) -> None:
        self.cache_service.save_kabutan_html_dir(path)

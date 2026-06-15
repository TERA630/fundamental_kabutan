"""Output cache management service."""

from __future__ import annotations

from datetime import date

from app.services.cache_service import CacheService
from app.ui_state_utils import current_date_iso


class OutputCacheService:
    def __init__(self, cache_service: CacheService | None = None):
        self.cache_service = cache_service or CacheService()

    def fetch_for_today(self, *, today: date | None = None) -> dict[str, str]:
        return self.cache_service.fetch_output_cache_for_today(today=today)

    def save_for_today(self, output_cache: dict[str, str], *, today: date | None = None) -> None:
        self.cache_service.save_output_cache_for_today(output_cache, today=today)

    def should_rotate(self, cache_date: str | None, *, today: date | None = None) -> bool:
        if cache_date is None:
            return False
        return cache_date != current_date_iso(today=today)

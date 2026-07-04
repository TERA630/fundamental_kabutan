"""Watchlist loading and persistence service."""

from __future__ import annotations

from pathlib import Path

from app.data.watchlist_repository import (
    fetch_watchlist_entries,
    fetch_watchlist_entries_with_sectors,
    parse_watchlist_entries_with_sectors,
    parse_watchlist_text,
)
from app.domain.models.watchlist import WatchlistEntry
from app.services.cache_service import CacheService


class WatchlistService:
    def __init__(self, cache_service: CacheService | None = None):
        self.cache_service = cache_service or CacheService()

    def load_from_file(self, path: Path) -> list[tuple[str, str]]:
        return fetch_watchlist_entries(path)

    def load_from_file_with_sectors(self, path: Path) -> list[WatchlistEntry]:
        return fetch_watchlist_entries_with_sectors(path)

    def parse_uploaded(self, data: bytes) -> list[tuple[str, str]]:
        entries = parse_watchlist_text(self._decode_watchlist_upload(data))
        if not entries:
            raise ValueError(
                "監視銘柄ファイルから銘柄を抽出できませんでした。対応形式例: '銘柄名 (1234)', '1234  銘柄名', '銘柄名,1234'"
            )
        return entries

    def parse_uploaded_with_sectors(self, data: bytes) -> list[WatchlistEntry]:
        entries = parse_watchlist_entries_with_sectors(self._decode_watchlist_upload(data))
        if not entries:
            raise ValueError(
                "監視銘柄ファイルから銘柄を抽出できませんでした。対応形式例: '銘柄名 (1234)', '1234  銘柄名', '銘柄名,1234'"
            )
        return entries

    def restore_watchlist_path(self) -> Path | None:
        return self.cache_service.fetch_watchlist_path()

    def save_watchlist_path(self, path: Path) -> None:
        self.cache_service.save_watchlist_path(path)

    def _decode_watchlist_upload(self, data: bytes) -> str:
        last_error: UnicodeDecodeError | None = None
        for encoding in ("utf-8", "utf-8-sig", "cp932"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise ValueError(f"監視銘柄ファイルを読み込めませんでした: {last_error}")

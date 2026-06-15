"""Use case for resolving cached watchlist file path."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolvedWatchlistPath:
    file_path: Path | None
    status: str
    message: str


@dataclass
class ResolveWatchlistPathUseCase:
    def fetch_resolved_watchlist_path(self, cached_path: Path | None) -> ResolvedWatchlistPath:
        if cached_path is None:
            return ResolvedWatchlistPath(None, "missing", "監視銘柄ファイルのキャッシュは未設定です。")
        try:
            if not cached_path.exists() or not cached_path.is_file():
                return ResolvedWatchlistPath(None, "missing", "前回の監視銘柄ファイルが見つかりません。再選択してください。")
        except OSError:
            return ResolvedWatchlistPath(None, "missing", "前回の監視銘柄ファイルにアクセスできません。再選択してください。")
        return ResolvedWatchlistPath(cached_path, "ok", "監視銘柄ファイルを前回設定から復元しました。")


__all__ = ["ResolvedWatchlistPath", "ResolveWatchlistPathUseCase"]

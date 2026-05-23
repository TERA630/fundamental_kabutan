"""Use case for resolving cached Kabutan HTML directory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolvedKabutanHtmlDir:
    dir_path: Path | None
    status: str
    message: str


@dataclass
class ResolveKabutanHtmlDirUseCase:
    def fetch_resolved_kabutan_html_dir(self, cached_dir: Path | None) -> ResolvedKabutanHtmlDir:
        if cached_dir is None:
            return ResolvedKabutanHtmlDir(None, "missing", "株探HTMLフォルダのキャッシュは未設定です。")
        if not cached_dir.exists() or not cached_dir.is_dir():
            return ResolvedKabutanHtmlDir(None, "missing", "前回の株探HTMLフォルダが見つかりません。再選択してください。")
        return ResolvedKabutanHtmlDir(cached_dir, "ok", "株探HTMLフォルダを前回設定から復元しました。")


__all__ = ["ResolvedKabutanHtmlDir", "ResolveKabutanHtmlDirUseCase"]

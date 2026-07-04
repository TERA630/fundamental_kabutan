"""File upload helpers for the Web UI."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from app.data.file_cache import FileCache
from app.domain.models.watchlist import WatchlistEntry
from app.services.watchlist_service import WatchlistService

UPLOAD_WATCHLIST_CACHE_NAME = "web_uploaded_watchlist.md"
UPLOAD_KABUTAN_HTML_DIR_NAME = "web_uploaded_kabutan_html"
UPLOAD_KABUTAN_PACKAGE_NAME = "web_uploaded_kabutan_html_package.zip"
KABUTAN_HTML_SUFFIXES = {".html", ".htm"}


class WebUploadWorkflow:
    def __init__(
        self,
        *,
        file_cache: FileCache,
        watchlist_service: WatchlistService | None = None,
    ):
        self.file_cache = file_cache
        self.watchlist_service = watchlist_service or WatchlistService()

    def parse_uploaded_watchlist(self, data: bytes) -> list[tuple[str, str]]:
        return self.watchlist_service.parse_uploaded(data)

    def parse_uploaded_watchlist_with_sectors(self, data: bytes) -> list[WatchlistEntry]:
        return self.watchlist_service.parse_uploaded_with_sectors(data)

    def load_uploaded_watchlist(self, data: bytes) -> tuple[list[tuple[str, str]], Path]:
        entries = self.parse_uploaded_watchlist(data)
        return entries, self.save_uploaded_watchlist(data)

    def load_uploaded_watchlist_with_sectors(self, data: bytes) -> tuple[list[WatchlistEntry], Path]:
        entries = self.parse_uploaded_watchlist_with_sectors(data)
        return entries, self.save_uploaded_watchlist(data)

    def load_watchlist_from_path(self, raw_path: str) -> tuple[list[tuple[str, str]], Path]:
        if not raw_path.strip():
            raise ValueError("監視銘柄ファイルをアップロードするか、パスを入力してください。")
        path = Path(raw_path).expanduser().resolve()
        return self.watchlist_service.load_from_file(path), path

    def load_watchlist_from_path_with_sectors(self, raw_path: str) -> tuple[list[WatchlistEntry], Path]:
        if not raw_path.strip():
            raise ValueError("監視銘柄ファイルをアップロードするか、パスを入力してください。")
        path = Path(raw_path).expanduser().resolve()
        return self.watchlist_service.load_from_file_with_sectors(path), path

    def save_uploaded_watchlist(self, data: bytes) -> Path:
        path = self.file_cache.base_dir / UPLOAD_WATCHLIST_CACHE_NAME
        path.write_bytes(data)
        return path

    def resolve_existing_dir(self, raw_path: str) -> Path:
        path = Path(raw_path.strip()).expanduser()
        if not raw_path.strip():
            raise ValueError("株探HTMLフォルダのコンテナ内パスを入力してください。")
        if not path.exists() or not path.is_dir():
            raise ValueError("株探HTMLフォルダが見つかりません。コンテナ内の既存ディレクトリを指定してください。")
        return path.resolve()

    def save_uploaded_kabutan_html_dir(self, uploaded_files: list[Any]) -> Path:
        files = [
            uploaded
            for uploaded in uploaded_files
            if uploaded is not None
            and uploaded.filename
            and Path(uploaded.filename).suffix.lower() in KABUTAN_HTML_SUFFIXES
        ]
        if not files:
            raise ValueError("株探HTMLフォルダにHTMLファイルが見つかりませんでした。")

        upload_dir = self.file_cache.base_dir / UPLOAD_KABUTAN_HTML_DIR_NAME
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        used_names: set[str] = set()
        for uploaded in files:
            source_name = Path(uploaded.filename).name
            target_name = _dedupe_filename(source_name, used_names)
            uploaded.save(upload_dir / target_name)
        return upload_dir.resolve()

    def save_uploaded_kabutan_html_package(self, uploaded_file: Any) -> Path:
        if uploaded_file is None or not uploaded_file.filename:
            raise ValueError("株探HTMLパッケージZipを選択してください。")
        if Path(uploaded_file.filename).suffix.lower() != ".zip":
            raise ValueError("株探HTMLパッケージはZipファイルを選択してください。")
        zip_path = self.file_cache.base_dir / UPLOAD_KABUTAN_PACKAGE_NAME
        uploaded_file.save(zip_path)
        return zip_path


def _dedupe_filename(filename: str, used_names: set[str]) -> str:
    path = Path(filename)
    candidate = path.name
    index = 2
    while candidate.lower() in used_names:
        candidate = f"{path.stem}_{index}{path.suffix}"
        index += 1
    used_names.add(candidate.lower())
    return candidate


__all__ = [
    "KABUTAN_HTML_SUFFIXES",
    "UPLOAD_KABUTAN_HTML_DIR_NAME",
    "UPLOAD_KABUTAN_PACKAGE_NAME",
    "UPLOAD_WATCHLIST_CACHE_NAME",
    "WebUploadWorkflow",
]

"""Data-layer file cache implementation."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

CACHE_DIR_NAME = ".fundamental_cache"


class FileCache:
    """単純なJSONファイルキャッシュ。API回数削減を最優先にする。"""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or (Path(__file__).resolve().parent.parent.parent / CACHE_DIR_NAME)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe_key = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
        return self.base_dir / f"{safe_key}.json"

    def get(self, key: str, ttl_sec: int | float) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            saved_at = float(payload.get("saved_at", 0))
            if time.time() - saved_at > ttl_sec:
                return None
            return payload.get("data")
        except Exception:
            return None

    def set(self, key: str, data: Any) -> None:
        path = self._path(key)
        tmp = path.with_suffix(path.suffix + ".tmp")
        payload = {"saved_at": time.time(), "data": data}
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            return

    def fetch_kabutan_html_dir_cache(self) -> Path | None:
        cached = self.get("kabutan_last_html_dir", ttl_sec=10**9)
        if not isinstance(cached, str) or not cached.strip():
            return None
        return Path(cached)

    def save_kabutan_html_dir_cache(self, path: Path) -> None:
        self.set("kabutan_last_html_dir", str(path.resolve()))

    def fetch_kabutan_package_zip_cache(self) -> Path | None:
        cached = self.get("kabutan_last_package_zip", ttl_sec=10**9)
        if not isinstance(cached, str) or not cached.strip():
            return None
        return Path(cached)

    def save_kabutan_package_zip_cache(self, path: Path) -> None:
        self.set("kabutan_last_package_zip", str(path.resolve()))

    def clear_kabutan_package_zip_cache(self) -> None:
        self.delete("kabutan_last_package_zip")

    def fetch_watchlist_path_cache(self) -> Path | None:
        cached = self.get("watchlist_last_path", ttl_sec=10**9)
        if not isinstance(cached, str) or not cached.strip():
            return None
        return Path(cached)

    def save_watchlist_path_cache(self, path: Path) -> None:
        self.set("watchlist_last_path", str(path.resolve()))

__all__ = ["FileCache", "CACHE_DIR_NAME"]

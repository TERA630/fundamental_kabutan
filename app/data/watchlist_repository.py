"""Data-layer repository for watchlist file loading/parsing."""

from __future__ import annotations

import re
from pathlib import Path

from app.domain.models.watchlist import WatchlistEntry

SECTOR_TAG_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("半導体材料・装置", ("半導体材料・装置", "半導体材料", "半導体装置")),
    ("電線・電力インフラ", ("電線・電力インフラ", "電線", "電力インフラ")),
    ("データセンター・電源、空調", ("データセンター・電源、空調", "データセンター", "電源", "空調")),
    ("電子部品・電子機器", ("電子部品・電子機器", "電子部品", "電子機器")),
    ("FA・機械・ロボット", ("FA・機械・ロボット", "FA", "機械", "ロボット")),
    ("防衛・重工", ("防衛・重工", "防衛", "重工")),
    ("商社・資源", ("商社・資源", "商社", "資源")),
    ("ディフェンシブ・内需", ("ディフェンシブ・内需", "ディフェンシブ", "内需")),
    ("水処理・環境インフラ", ("水処理・環境インフラ", "水処理", "環境インフラ")),
)

_TAG_BOUNDARY_CHARS = r"一-龥ぁ-んァ-ンA-Za-z0-9"


def parse_watchlist_text(text: str) -> list[tuple[str, str]]:
    return [entry.as_tuple() for entry in parse_watchlist_entries_with_sectors(text)]


def parse_watchlist_entries_with_sectors(text: str) -> list[WatchlistEntry]:
    patterns = [
        re.compile(r"[-*]?\s*([^\n()（）]+?)\s*[\(（]\s*(\d{4})\s*[\)）]"),
        re.compile(r"^\s*(\d{4})\s*[-,:：\t ]+\s*([^\n]+?)\s*$"),
        re.compile(r"^\s*([^\n,，\t]+?)\s*[,，\t]\s*(\d{4})(?:\s*[,，\t].*)?$"),
    ]
    entries: list[WatchlistEntry] = []
    seen_codes: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        stock_name = ""
        code4 = ""
        for idx, pattern in enumerate(patterns):
            matched = pattern.search(line)
            if not matched:
                continue
            if idx == 1:
                code4 = matched.group(1).strip()
                stock_name = _strip_sector_tags(matched.group(2).strip())
            else:
                stock_name = _strip_sector_tags(matched.group(1).strip())
                code4 = matched.group(2).strip()
            break

        if not code4 or code4 in seen_codes:
            continue

        seen_codes.add(code4)
        entries.append(WatchlistEntry(stock_name, code4, _extract_sector_tags(line)))

    return entries


def _extract_sector_tags(line: str) -> tuple[str, ...]:
    sectors: list[str] = []
    for canonical, aliases in SECTOR_TAG_ALIASES:
        if any(_contains_tag_alias(line, alias) for alias in aliases):
            sectors.append(canonical)
    return tuple(sectors)


def _strip_sector_tags(value: str) -> str:
    stripped = value
    for _canonical, aliases in SECTOR_TAG_ALIASES:
        for alias in aliases:
            stripped = re.sub(
                rf"(?<![{_TAG_BOUNDARY_CHARS}]){re.escape(alias)}(?![{_TAG_BOUNDARY_CHARS}])",
                " ",
                stripped,
            )
    stripped = re.sub(r"[\s,，:：/|｜#\[\]【】()（）・、-]+$", "", stripped)
    return stripped.strip()


def _contains_tag_alias(line: str, alias: str) -> bool:
    return re.search(rf"(?<![{_TAG_BOUNDARY_CHARS}]){re.escape(alias)}(?![{_TAG_BOUNDARY_CHARS}])", line) is not None


def fetch_watchlist_entries(path: Path) -> list[tuple[str, str]]:
    return [entry.as_tuple() for entry in fetch_watchlist_entries_with_sectors(path)]


def fetch_watchlist_entries_with_sectors(path: Path) -> list[WatchlistEntry]:
    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp932"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    else:
        raise ValueError(f"監視銘柄ファイルを読み込めませんでした: {last_error}")

    parsed_entries = parse_watchlist_entries_with_sectors(text)
    if not parsed_entries:
        raise ValueError(
            "監視銘柄ファイルから銘柄を抽出できませんでした。対応形式例: '銘柄名 (1234)', '1234  銘柄名', '銘柄名,1234'"
        )

    return parsed_entries


__all__ = [
    "SECTOR_TAG_ALIASES",
    "fetch_watchlist_entries",
    "fetch_watchlist_entries_with_sectors",
    "parse_watchlist_entries_with_sectors",
    "parse_watchlist_text",
]

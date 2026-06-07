"""GUI state helper functions and shared value builders."""

from __future__ import annotations

from datetime import date
from pathlib import Path


def current_date_iso(*, today: date | None = None) -> str:
    return (today or date.today()).isoformat()


def should_rotate_output_cache(cache_date: str | None, *, today: date | None = None) -> bool:
    if cache_date is None:
        return False
    return cache_date != current_date_iso(today=today)


def build_stock_choices(watchlist: list[tuple[str, str]]) -> tuple[list[str], dict[str, tuple[str, str]]]:
    values: list[str] = []
    mapping: dict[str, tuple[str, str]] = {}
    for name, code in watchlist:
        display = f"{name} ({code})"
        values.append(display)
        mapping[display] = (name, code)
    return values, mapping


def get_selected_stock(display_to_code: dict[str, tuple[str, str]], label: str) -> tuple[str, str] | None:
    key = label.strip()
    if not key:
        return None
    return display_to_code.get(key)


def build_default_output_filename(selected: tuple[str, str] | None) -> str:
    if selected is None:
        return "stock_fundamental_prompt.txt"
    _, code = selected
    return f"stock_fundamental_prompt_{code}.txt"


def build_output_cache_key(code4: str, kabutan_html_dir: Path | None) -> str:
    dir_part = str(kabutan_html_dir.resolve()) if kabutan_html_dir is not None else "-"
    return f"{code4}|{dir_part}"

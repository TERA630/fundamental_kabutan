"""GUI state model and helper builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from app.domain.models.cf_scoring_result import CfScoringResult
from app.gui_state_utils import (
    build_default_output_filename,
    build_output_cache_key,
    build_stock_choices,
    current_date_iso,
    get_selected_stock,
    should_rotate_output_cache,
)


@dataclass
class GuiState:
    """GUI表示に必要な状態を保持する。"""

    watchlist_path: Path | None = None
    kabutan_html_dir: Path | None = None
    watchlist: list[tuple[str, str]] = field(default_factory=list)
    display_to_code: dict[str, tuple[str, str]] = field(default_factory=dict)
    output_cache: dict[str, str] = field(default_factory=dict)
    scoring_cache: dict[str, CfScoringResult] = field(default_factory=dict)
    output_cache_date: str | None = None
    is_fetching: bool = False





__all__ = [
    "GuiState",
    "current_date_iso",
    "should_rotate_output_cache",
    "build_stock_choices",
    "get_selected_stock",
    "build_default_output_filename",
    "build_output_cache_key",
]

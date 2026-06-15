"""GUI state model and helper builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from app.domain.models.cf_scoring_result import CfScoringResult
from app.ui_state_utils import (
    build_default_output_filename,
    build_stock_choices,
    get_selected_stock,
)


@dataclass
class GuiState:
    """GUI表示に必要な状態を保持する。"""

    watchlist_path: Path | None = None
    kabutan_html_dir: Path | None = None
    watchlist: list[tuple[str, str]] = field(default_factory=list)
    display_to_code: dict[str, tuple[str, str]] = field(default_factory=dict)
    scoring_cache: dict[str, CfScoringResult] = field(default_factory=dict)
    is_fetching: bool = False





__all__ = [
    "GuiState",
    "build_stock_choices",
    "get_selected_stock",
    "build_default_output_filename",
]

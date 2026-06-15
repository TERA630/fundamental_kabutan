"""Backward-compatible import surface for shared UI state helpers.

Prefer importing from app.ui_state_utils in new code.
"""

from __future__ import annotations

from app.ui_state_utils import (
    build_default_output_filename,
    build_output_cache_key,
    build_stock_choices,
    current_date_iso,
    get_selected_stock,
    should_rotate_output_cache,
)

__all__ = [
    "build_default_output_filename",
    "build_output_cache_key",
    "build_stock_choices",
    "current_date_iso",
    "get_selected_stock",
    "should_rotate_output_cache",
]

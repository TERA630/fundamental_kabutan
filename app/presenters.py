"""Presentation facade kept for existing GUI and tests."""

from __future__ import annotations

from app.domain.builders.kabutan_output import build_kabutan_forecast_output
from app.presentation.cf_scoring_output import (
    build_cf_scoring_sections,
    build_cf_scoring_summary_text,
)
from app.presentation.fundamental_output import (
    build_base_fundamental_output,
    build_fundamental_output,
)
from app.presentation.legacy_fallback import (
    build_cf_scoring_summary_lines,
    insert_summary_after_indicator,
)

__all__ = [
    "build_base_fundamental_output",
    "build_cf_scoring_sections",
    "build_cf_scoring_summary_lines",
    "build_cf_scoring_summary_text",
    "build_fundamental_output",
    "build_kabutan_forecast_output",
    "insert_summary_after_indicator",
]



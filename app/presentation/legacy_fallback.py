"""Fallback formatting helpers for legacy text output."""

from __future__ import annotations

from app.domain.models.cf_scoring_result import CfScoringResult
from app.domain.models.display_sections import DisplaySections
from app.presentation.cf_scoring_output import (
    build_cf_scoring_sections,
    build_cf_scoring_summary_text,
)
from app.presentation.display_formatter import format_sections


def build_cf_scoring_summary_lines(scoring: CfScoringResult) -> list[str]:
    sections = build_cf_scoring_sections(scoring, include_summary=True)[:1]
    text = format_sections(DisplaySections(sections=sections))
    return text.splitlines()


def insert_summary_after_indicator(base_output: str, scoring: CfScoringResult) -> str:
    lines = base_output.splitlines()
    insert_at = next((index + 1 for index, line in enumerate(lines) if line.startswith("時価総額：")), None)
    if insert_at is None:
        insert_at = 1 if lines else 0
    return "\n".join([*lines[:insert_at], *build_cf_scoring_summary_lines(scoring), *lines[insert_at:]])


def append_scoring_fallback(base_output: str, scoring: CfScoringResult | None) -> str:
    if scoring is None:
        return base_output
    if "総合評価：" in base_output or "総合評価 " in base_output:
        return base_output
    output = insert_summary_after_indicator(base_output, scoring)
    return f"{output}\n{build_cf_scoring_summary_text(scoring)}"


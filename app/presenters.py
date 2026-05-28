"""Presentation helpers: bridge GUI use-cases and domain/output builders."""

from __future__ import annotations
import logging
from typing import Any

from app.domain.builders.fundamental_output import build_fundamental_output_text, build_fundamental_output_sections
from app.domain.builders.kabutan_output import build_kabutan_forecast_output
from app.domain.models.cf_scoring_result import CfScoringResult
from app.domain.models.display_sections import (
    DisplaySections,
    OpeningSummarySection,
    RuleNotesSection,
    ScoreCategorySection,
    ScoreSummarySection,
    Section,
    SummarySection,
    ValuationTableSection,
)
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.quarterly_financials import QuarterlyMetricRow
from app.presentation.display_formatter import format_sections


logger = logging.getLogger(__name__)


def build_cf_scoring_sections(scoring: CfScoringResult, *, include_summary: bool = False) -> list[Section]:
    sections: list[Section] = []
    if include_summary:
        sections.append(
            ScoreSummarySection(
                judgement=scoring.total.judgement,
                total_points=scoring.total.total_points,
                max_points=scoring.total.max_points,
                version=scoring.version,
                investment_category=scoring.total.investment_category,
                investment_strategy=scoring.total.investment_strategy,
                as_of=scoring.as_of,
            )
        )

    sections.extend(
        [
            ScoreCategorySection("Quality", scoring.quality.subtotal, scoring.quality.max_points, list(scoring.quality.metrics)),
            ScoreCategorySection("Growth", scoring.growth.subtotal, scoring.growth.max_points, list(scoring.growth.metrics)),
            ScoreCategorySection("Valuation", scoring.valuation.subtotal, scoring.valuation.max_points, list(scoring.valuation.metrics)),
            RuleNotesSection(
                [
                    note
                    for category in (scoring.quality, scoring.growth, scoring.valuation)
                    for metric in category.metrics
                    for note in metric.rule_notes
                ]
            ),
        ]
    )
    return sections


def build_cf_scoring_summary_text(scoring: CfScoringResult) -> str:
    return "\n" + format_sections(DisplaySections(sections=build_cf_scoring_sections(scoring)))


def _build_opening_summary_section(
    summary: SummarySection,
    scoring: CfScoringResult,
    *,
    growth_phase: str | None,
    per_level: str | None,
    roic_level: str | None,
) -> OpeningSummarySection:
    return OpeningSummarySection(
        company_name=summary.company_name,
        code4=summary.code4,
        price=summary.price,
        market_cap=summary.market_cap,
        market_cap_class=None,
        judgement=scoring.total.judgement,
        total_points=scoring.total.total_points,
        max_points=scoring.total.max_points,
        growth_phase=growth_phase,
        per_level=per_level,
        roic_level=roic_level,
        investment_strategy=scoring.total.investment_strategy,
    )


def _merge_scoring_sections(
    sections: DisplaySections,
    scoring: CfScoringResult,
    *,
    growth_phase: str | None,
    per_level: str | None,
    roic_level: str | None,
) -> DisplaySections:
    merged: list[Section] = []
    scoring_details = build_cf_scoring_sections(scoring)
    inserted_summary = False
    inserted_details = False

    for section in sections.sections:
        if isinstance(section, SummarySection) and not inserted_summary:
            merged.append(
                _build_opening_summary_section(
                    section,
                    scoring,
                    growth_phase=growth_phase,
                    per_level=per_level,
                    roic_level=roic_level,
                )
            )
            inserted_summary = True
            continue

        merged.append(section)
        if isinstance(section, ValuationTableSection) and not inserted_details:
            merged.extend(scoring_details)
            inserted_details = True

    if not inserted_details:
        merged.extend(scoring_details)
    return DisplaySections(sections=merged)


def build_cf_scoring_summary_lines(scoring: CfScoringResult) -> list[str]:
    text = format_sections(DisplaySections(sections=build_cf_scoring_sections(scoring, include_summary=True)[:1]))
    return text.splitlines()


def _insert_summary_after_indicator(base_output: str, scoring: CfScoringResult) -> str:
    lines = base_output.splitlines()
    insert_at = next((index + 1 for index, line in enumerate(lines) if line.startswith("時価総額：")), None)
    if insert_at is None:
        insert_at = 1 if lines else 0
    return "\n".join([*lines[:insert_at], *build_cf_scoring_summary_lines(scoring), *lines[insert_at:]])


def build_fundamental_output(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
    kabutan_forecast_pair: KabutanForecastPair | None = None,
    kabutan_source: str = "none",
    kabutan_source_message: str | None = None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
    quarterly_metric_rows: tuple[QuarterlyMetricRow, ...] = (),
    quarterly_message: str | None = None,
    cf_scoring_result: CfScoringResult | None = None,
    growth_phase: str | None = None,
    per_level: str | None = None,
    roic_level: str | None = None,
) -> str:
    """ドメイン層の出力生成ビルダーを呼び出す。"""
    base_output = build_fundamental_output_text(
        name=name,
        code4=code4,
        master=master,
        price=price,
        market_cap=market_cap,
        market_snapshot=market_snapshot,
        kabutan_forecast_pair=kabutan_forecast_pair,
    )
    # Prefer DTO-based path: build sections and format them. Fallback to legacy text builder.
    try:
        sections = build_fundamental_output_sections(
            name=name,
            code4=code4,
            master=master,
            price=price,
            market_cap=market_cap,
            market_snapshot=market_snapshot,
            kabutan_forecast_pair=kabutan_forecast_pair,
        )
        if cf_scoring_result is not None:
            sections = _merge_scoring_sections(
                sections,
                cf_scoring_result,
                growth_phase=growth_phase,
                per_level=per_level,
                roic_level=roic_level,
            )
        base_output = format_sections(sections)
    except Exception:
        # If anything goes wrong, keep using the legacy text builder
        logger.debug("DTO formatting path failed, using legacy text builder", exc_info=True)
    if cf_scoring_result is not None and "総合評価：" not in base_output and "総合評価 " not in base_output:
        base_output = _insert_summary_after_indicator(base_output, cf_scoring_result)
        base_output = f"{base_output}\n{build_cf_scoring_summary_text(cf_scoring_result)}"
    output = build_kabutan_forecast_output(
        base_output,
        kabutan_forecast_pair,
        kabutan_source,
        kabutan_source_message,
        kabutan_cashflow_rows,
        market_cap,
        financial_metric_rows,
        quarterly_metric_rows,
        quarterly_message,
        cf_scoring_result,
    )
    return output

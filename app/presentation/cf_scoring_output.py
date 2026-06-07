"""Presentation sections for CF scoring output."""

from __future__ import annotations

from app.domain.models.cf_scoring_result import CfScoringResult, MetricScore
from app.domain.models.display_sections import (
    DisplaySections,
    OpeningSummarySection,
    RuleNotesSection,
    ScoreBreakdownSection,
    ScoreCategorySection,
    ScoreSummarySection,
    Section,
    SummarySection,
    ValuationTableSection,
)
from app.domain.policies.cf_scoring import score_sales_cagr_3y
from app.presentation.display_formatter import format_sections


def _rank_operating_profit_cagr(value: float | None) -> str:
    return score_sales_cagr_3y(value).rank


def _build_growth_display_metrics(
    scoring: CfScoringResult, operating_profit_cagr_3y: float | None
) -> list[MetricScore]:
    by_id = {metric.metric_id: metric for metric in scoring.growth.metrics}
    metrics: list[MetricScore] = []
    for metric_id in ("sales_cagr_3y", "eps_cagr_3y"):
        metric = by_id.get(metric_id)
        if metric is not None:
            metrics.append(metric)
        if metric_id == "sales_cagr_3y" and operating_profit_cagr_3y is not None:
            metrics.append(
                MetricScore(
                    "operating_profit_cagr_3y",
                    "growth",
                    operating_profit_cagr_3y,
                    _rank_operating_profit_cagr(operating_profit_cagr_3y),
                    0,
                    0,
                )
            )
    return metrics


def build_cf_scoring_sections(
    scoring: CfScoringResult,
    *,
    include_summary: bool = False,
    operating_profit_cagr_3y: float | None = None,
) -> list[Section]:
    sections: list[Section] = []
    if include_summary:
        sections.append(
            ScoreSummarySection(
                judgement=scoring.total.judgement,
                total_points=scoring.total.total_points,
                max_points=scoring.total.max_points,
                version=scoring.version,
                investment_category=scoring.total.investment_category,
                as_of=scoring.as_of,
            )
        )

    sections.extend(
        [
            ScoreBreakdownSection(
                quality_points=scoring.quality.subtotal,
                growth_points=scoring.growth.subtotal,
                valuation_points=scoring.valuation.subtotal,
            ),
            ScoreCategorySection(
                "Quality",
                scoring.quality.subtotal,
                scoring.quality.max_points,
                list(scoring.quality.metrics),
            ),
            ScoreCategorySection(
                "Growth",
                scoring.growth.subtotal,
                scoring.growth.max_points,
                _build_growth_display_metrics(scoring, operating_profit_cagr_3y),
            ),
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
    )


def merge_scoring_sections(
    sections: DisplaySections,
    scoring: CfScoringResult,
    *,
    growth_phase: str | None,
    operating_profit_cagr_3y: float | None,
    per_level: str | None,
    roic_level: str | None,
) -> DisplaySections:
    merged: list[Section] = []
    scoring_details = build_cf_scoring_sections(
        scoring, operating_profit_cagr_3y=operating_profit_cagr_3y
    )
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


"""Domain use-case: merge fundamental and technical summaries into Hybrid Summary."""

from __future__ import annotations

from app.domain.models.fundamental_summary import FundamentalSummaryTable
from app.domain.models.hybrid_summary import (
    HybridSummaryRow,
    HybridSummaryTable,
    SkippedHybridSummaryStock,
)
from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryTable
from app.domain.policies.hybrid_classification import TAG_ORDER, classify_hybrid_candidate


class HybridSummaryService:
    """Builds cross-domain candidate rows from existing summary tables."""

    def build_summary_table(
        self,
        *,
        fundamental_table: FundamentalSummaryTable,
        technical_table: TechnicalSummaryTable,
    ) -> HybridSummaryTable:
        fundamental_by_code = {row.code4: row for row in fundamental_table.rows}
        technical_by_code = {row.code4: row for row in technical_table.rows}
        rows: list[HybridSummaryRow] = []

        for code4, technical_row in technical_by_code.items():
            fundamental_row = fundamental_by_code.get(code4)
            if fundamental_row is None:
                continue
            classification = classify_hybrid_candidate(
                fundamental_score=fundamental_row.total_score,
                quality_score=fundamental_row.quality_score,
                latest=technical_row.latest,
                vwap=technical_row.vwap,
                dev25_pct=technical_row.dev25_pct,
                day_close_position=technical_row.day_close_position,
                volume_vs_avg20_pct=technical_row.volume_vs_avg20_pct,
                high_breakout_count=technical_row.high_breakout_count,
                low_lower_count=technical_row.low_lower_count,
                previous_low_maintained=technical_row.previous_low_maintained,
                collapse_risk_score=technical_row.collapse_risk_score,
                resistance_upside_pct=_resistance_upside_pct(
                    latest=technical_row.latest,
                    resistance_lines=technical_row.resistance_lines,
                ),
                volume_spike_bearish=technical_row.volume_spike_bearish,
            )
            if classification is None:
                continue
            rows.append(
                HybridSummaryRow(
                    name=technical_row.name,
                    code4=technical_row.code4,
                    tag=classification.tag,
                    tag_label=classification.tag_label,
                    fundamental_score=fundamental_row.total_score,
                    quality_score=fundamental_row.quality_score,
                    technical_rank=technical_row.rank,
                    technical_rank_label=technical_row.rank_label,
                    latest=technical_row.latest,
                    dev25_pct=technical_row.dev25_pct,
                    vwap_diff_pct=technical_row.vwap_diff_pct,
                    day_close_position=technical_row.day_close_position,
                    volume_vs_avg20_pct=technical_row.volume_vs_avg20_pct,
                    collapse_risk_score=technical_row.collapse_risk_score,
                    resistance_upside_pct=_resistance_upside_pct(
                        latest=technical_row.latest,
                        resistance_lines=technical_row.resistance_lines,
                    ),
                    reasons=classification.reasons,
                )
            )

        return HybridSummaryTable(
            rows=tuple(sorted(rows, key=_sort_key)),
            skipped=_build_skipped(fundamental_table, technical_table, fundamental_by_code, technical_by_code),
        )


def _resistance_upside_pct(
    *,
    latest: float | None,
    resistance_lines: tuple[TechnicalSummaryLine, ...],
) -> float | None:
    if latest in (None, 0) or not resistance_lines:
        return None
    return ((resistance_lines[0].price / latest) - 1) * 100


def _build_skipped(
    fundamental_table: FundamentalSummaryTable,
    technical_table: TechnicalSummaryTable,
    fundamental_by_code: dict[str, object],
    technical_by_code: dict[str, object],
) -> tuple[SkippedHybridSummaryStock, ...]:
    skipped: list[SkippedHybridSummaryStock] = []
    skipped.extend(
        SkippedHybridSummaryStock(item.name, item.code4, f"Fundamental: {item.reason}")
        for item in fundamental_table.skipped
    )
    skipped.extend(
        SkippedHybridSummaryStock(item.name, item.code4, f"Technical: {item.reason}")
        for item in technical_table.skipped
    )
    skipped.extend(
        SkippedHybridSummaryStock(row.name, row.code4, "Technical行なし")
        for row in fundamental_table.rows
        if row.code4 not in technical_by_code
    )
    skipped.extend(
        SkippedHybridSummaryStock(row.name, row.code4, "Fundamental行なし")
        for row in technical_table.rows
        if row.code4 not in fundamental_by_code
    )
    return tuple(skipped)


_TAG_ORDER_INDEX = {tag: index for index, tag in enumerate(TAG_ORDER)}


def _sort_key(row: HybridSummaryRow) -> tuple[int, int, int, str]:
    collapse_score = row.collapse_risk_score if row.collapse_risk_score is not None else -1
    return (
        _TAG_ORDER_INDEX.get(row.tag, len(TAG_ORDER)),
        -collapse_score if row.tag == "M2" else -row.fundamental_score,
        -(row.quality_score or 0),
        row.code4,
    )


__all__ = ["HybridSummaryService"]

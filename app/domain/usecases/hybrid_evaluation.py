"""Domain use-case: build single-stock Hybrid evaluation."""

from __future__ import annotations

from app.domain.models.fundamental_summary import FundamentalSummaryRow
from app.domain.models.hybrid_evaluation import HybridEvaluation
from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryRow
from app.domain.policies.hybrid_classification import classify_hybrid_candidate


class HybridEvaluationService:
    """Applies Hybrid classification to one fundamental row and one technical row."""

    def build_evaluation(
        self,
        *,
        fundamental_row: FundamentalSummaryRow,
        technical_row: TechnicalSummaryRow,
    ) -> HybridEvaluation:
        resistance_upside_pct = _resistance_upside_pct(
            latest=technical_row.latest,
            resistance_lines=technical_row.resistance_lines,
        )
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
            resistance_upside_pct=resistance_upside_pct,
            volume_spike_bearish=technical_row.volume_spike_bearish,
        )
        return HybridEvaluation(
            name=technical_row.name,
            code4=technical_row.code4,
            tag=None if classification is None else classification.tag,
            tag_label=None if classification is None else classification.tag_label,
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
            resistance_upside_pct=resistance_upside_pct,
            reasons=() if classification is None else classification.reasons,
        )


def _resistance_upside_pct(
    *,
    latest: float | None,
    resistance_lines: tuple[TechnicalSummaryLine, ...],
) -> float | None:
    if latest in (None, 0) or not resistance_lines:
        return None
    return ((resistance_lines[0].price / latest) - 1) * 100


__all__ = ["HybridEvaluationService"]

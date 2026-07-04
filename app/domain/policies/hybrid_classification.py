"""Classification policy for Hybrid evaluation candidate tags."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.models.hybrid_evaluation import HybridEvaluationTag

TAG_LABELS: dict[HybridEvaluationTag, str] = {
    "F1": "高ファンダ深押し反転候補",
    "F2": "高Quality再評価候補",
    "M1": "過熱継続候補",
    "M2": "過熱危険",
}

TAG_ORDER: tuple[HybridEvaluationTag, ...] = ("M2", "M1", "F1", "F2")


@dataclass(frozen=True)
class HybridClassification:
    tag: HybridEvaluationTag
    tag_label: str
    reasons: tuple[str, ...]


def classify_hybrid_candidate(
    *,
    fundamental_score: int | None,
    quality_score: int | None,
    latest: float | None,
    vwap: float | None,
    dev25_pct: float | None,
    day_close_position: float | None,
    volume_vs_avg20_pct: float | None,
    high_breakout_count: int | None,
    low_lower_count: int | None,
    previous_low_maintained: bool | None,
    collapse_risk_score: int | None,
    resistance_upside_pct: float | None,
    volume_spike_bearish: bool | None,
) -> HybridClassification | None:
    """Return the first matching Hybrid evaluation tag by risk-first priority."""

    vwap_up = latest is not None and vwap is not None and latest > vwap
    vwap_down = latest is not None and vwap is not None and latest < vwap
    close_position_pct = _position_pct(day_close_position)

    if _gt(dev25_pct, 8) and any(
        (
            _gte(collapse_risk_score, 5),
            vwap_down,
            close_position_pct is not None and close_position_pct < 40,
            volume_spike_bearish is True,
        )
    ):
        reasons = []
        if _gte(collapse_risk_score, 5):
            reasons.append(f"崩れ{collapse_risk_score}")
        if vwap_down:
            reasons.append("VWAP下")
        if close_position_pct is not None and close_position_pct < 40:
            reasons.append(f"終端{close_position_pct:.0f}%")
        if volume_spike_bearish is True:
            reasons.append("出来高150%以上陰線")
        return _classification("M2", tuple(reasons))

    if (
        _gt(dev25_pct, 8)
        and collapse_risk_score is not None
        and collapse_risk_score <= 3
        and vwap_up
        and _gte(close_position_pct, 60)
        and previous_low_maintained is True
        and _gte(high_breakout_count, 1)
    ):
        return _classification(
            "M1",
            (
                f"崩れ{collapse_risk_score}",
                f"高値更新{high_breakout_count}",
                "前日安値維持",
            ),
        )

    if (
        _gte(fundamental_score, 60)
        and dev25_pct is not None
        and dev25_pct <= -3
        and vwap_up
        and _gte(close_position_pct, 60)
        and _gte(high_breakout_count, 1)
        and low_lower_count is not None
        and low_lower_count <= 1
        and _gte(volume_vs_avg20_pct, 80)
    ):
        return _classification(
            "F1",
            (
                f"F{fundamental_score}",
                f"高値更新{high_breakout_count}",
                f"安値切下げ{low_lower_count}",
                f"出来高{volume_vs_avg20_pct:.0f}%",
            ),
        )

    if (
        _gte(fundamental_score, 60)
        and _gte(quality_score, 40)
        and dev25_pct is not None
        and -3 < dev25_pct <= 4
        and vwap_up
        and _gte(close_position_pct, 60)
        and _has_resistance_upside(resistance_upside_pct)
    ):
        resistance_reason = (
            "抵抗なし"
            if resistance_upside_pct is None
            else f"抵抗余地{resistance_upside_pct:.1f}%"
        )
        return _classification("F2", (f"F{fundamental_score}", f"Q{quality_score}", resistance_reason))

    return None


def _classification(tag: HybridEvaluationTag, reasons: tuple[str, ...]) -> HybridClassification:
    return HybridClassification(tag=tag, tag_label=TAG_LABELS[tag], reasons=reasons)


def _has_resistance_upside(value: float | None) -> bool:
    return value is None or value >= 3


def _position_pct(value: float | None) -> float | None:
    return None if value is None else value * 100


def _gte(value: float | int | None, threshold: float | int) -> bool:
    return value is not None and value >= threshold


def _gt(value: float | int | None, threshold: float | int) -> bool:
    return value is not None and value > threshold


__all__ = [
    "TAG_LABELS",
    "TAG_ORDER",
    "HybridClassification",
    "classify_hybrid_candidate",
]

"""Text builder for single-stock Hybrid evaluation."""

from __future__ import annotations

from app.domain.models.hybrid_evaluation import HybridEvaluation


def build_hybrid_evaluation_text(evaluation: HybridEvaluation) -> str:
    lines = [
        "■Hybrid評価",
        f"{evaluation.name}({evaluation.code4})",
    ]
    if evaluation.matched:
        lines.append(f"分類：{evaluation.tag} {evaluation.tag_label}")
    else:
        lines.append("分類：該当なし")
    lines.extend(
        [
            (
                f"F：{evaluation.fundamental_score} / "
                f"Q：{_fmt_optional_int(evaluation.quality_score)} / "
                f"Tech：{evaluation.technical_rank} {evaluation.technical_rank_label}"
            ),
            (
                f"現在値：{_fmt_price(evaluation.latest)}円 / "
                f"25ME dev：{_fmt_pct(evaluation.dev25_pct)} / "
                f"VWAP：{_fmt_pct(evaluation.vwap_diff_pct)}"
            ),
            (
                f"終端：{_fmt_position(evaluation.day_close_position)} / "
                f"出来高：{_fmt_pct_unsigned(evaluation.volume_vs_avg20_pct)} / "
                f"崩れ：{_fmt_optional_int(evaluation.collapse_risk_score)} / "
                f"抵抗余地：{_fmt_resistance_upside(evaluation.resistance_upside_pct)}"
            ),
            f"理由：{_fmt_reasons(evaluation.reasons)}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_hybrid_evaluation_unavailable_text(*, name: str, code4: str, reason: str) -> str:
    return f"■Hybrid評価\n{name}({code4})\n評価不可：{reason}\n"


def _fmt_reasons(values: tuple[str, ...]) -> str:
    return " / ".join(values) if values else "該当条件なし"


def _fmt_optional_int(value: int | None) -> str:
    return "N/A" if value is None else str(value)


def _fmt_price(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.0f}"


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.1f}%"


def _fmt_pct_unsigned(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0f}%"


def _fmt_position(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.0f}%"


def _fmt_resistance_upside(value: float | None) -> str:
    return "Open" if value is None else f"{value:.1f}%"


__all__ = ["build_hybrid_evaluation_text", "build_hybrid_evaluation_unavailable_text"]

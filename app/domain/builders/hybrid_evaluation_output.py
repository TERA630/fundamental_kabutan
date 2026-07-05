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
                f"Q：{_fmt_optional_int(evaluation.quality_score)}"
            ),
            f"理由：{_fmt_reasons(evaluation.reasons)}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_hybrid_evaluation_unavailable_text(*, name: str, code4: str, reason: str) -> str:
    return f"■Hybrid評価\n評価不可：{reason}\n"


def _fmt_reasons(values: tuple[str, ...]) -> str:
    return " / ".join(values) if values else "該当条件なし"


def _fmt_optional_int(value: int | None) -> str:
    return "N/A" if value is None else str(value)


__all__ = ["build_hybrid_evaluation_text", "build_hybrid_evaluation_unavailable_text"]

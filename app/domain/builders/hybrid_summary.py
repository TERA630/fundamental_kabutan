"""Markdown builder for watchlist-level Hybrid Summary."""

from __future__ import annotations

from app.domain.models.hybrid_summary import HybridSummaryRow, HybridSummaryTable
from app.domain.policies.hybrid_classification import TAG_LABELS, TAG_ORDER


def build_hybrid_summary_markdown(table: HybridSummaryTable) -> str:
    lines = ["# Hybrid Summary", ""]
    rows_by_tag = {tag: [row for row in table.rows if row.tag == tag] for tag in TAG_ORDER}
    for tag in TAG_ORDER:
        rows = rows_by_tag[tag]
        if not rows:
            continue
        lines.extend(
            [
                f"## {tag} {TAG_LABELS[tag]}",
                "",
                "| 分類 | 銘柄 | F | Q | Tech | 現在値 | 25ME dev | VWAP | 終端 | 出来高 | 崩れ | 抵抗余地 | 理由 |",
                "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        lines.extend(_format_row(row) for row in rows)
        lines.append("")

    if not table.rows:
        lines.extend(["該当銘柄なし", ""])

    if table.skipped:
        lines.extend(["## Skipped", ""])
        lines.extend(f"- {item.name}({item.code4}): {item.reason}" for item in table.skipped)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _format_row(row: HybridSummaryRow) -> str:
    return (
        f"| {row.tag} {row.tag_label} "
        f"| {row.name}({row.code4}) "
        f"| {row.fundamental_score} "
        f"| {_fmt_optional_int(row.quality_score)} "
        f"| {row.technical_rank} {row.technical_rank_label} "
        f"| {_fmt_price(row.latest)}円 "
        f"| {_fmt_pct(row.dev25_pct)} "
        f"| {_fmt_pct(row.vwap_diff_pct)} "
        f"| {_fmt_position(row.day_close_position)} "
        f"| {_fmt_pct_unsigned(row.volume_vs_avg20_pct)} "
        f"| {_fmt_optional_int(row.collapse_risk_score)} "
        f"| {_fmt_resistance_upside(row.resistance_upside_pct)} "
        f"| {' / '.join(row.reasons)} |"
    )


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


__all__ = ["build_hybrid_summary_markdown"]

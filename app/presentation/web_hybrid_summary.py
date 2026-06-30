"""Web presentation helper for Hybrid Summary display."""

from __future__ import annotations

from html import escape
from typing import Callable

from app.domain.models.hybrid_summary import HybridSummaryRow, HybridSummaryTable
from app.domain.policies.hybrid_classification import TAG_LABELS, TAG_ORDER


DetailUrlBuilder = Callable[[str, str], str]


def build_hybrid_summary_html(
    table: HybridSummaryTable,
    detail_url_builder: DetailUrlBuilder | None = None,
) -> str:
    sections = [
        '<section class="output-block summary-output hybrid-summary-output">',
        "<h2>Hybrid Summary</h2>",
    ]
    if not table.rows:
        sections.append("<p>該当銘柄なし</p>")
    for tag in TAG_ORDER:
        rows = [row for row in table.rows if row.tag == tag]
        if not rows:
            continue
        sections.append(f'<h3 class="summary-rank-heading">{tag} {escape(TAG_LABELS[tag])}</h3>')
        sections.append('<div class="table-scroll">')
        sections.append('<table class="fundamental-table summary-table hybrid-summary-table">')
        sections.append(
            "<thead><tr>"
            "<th>分類</th><th>銘柄</th><th>F</th><th>Q</th><th>Tech</th><th>現在値</th>"
            "<th>25ME dev</th><th>VWAP</th><th>終端</th><th>出来高</th><th>崩れ</th>"
            "<th>抵抗余地</th><th>理由</th>"
            "</tr></thead><tbody>"
        )
        sections.extend(_build_row_html(row, detail_url_builder=detail_url_builder) for row in rows)
        sections.append("</tbody></table></div>")
    sections.append(_build_skipped_html(table))
    sections.append("</section>")
    return "".join(sections)


def _build_row_html(row: HybridSummaryRow, *, detail_url_builder: DetailUrlBuilder | None) -> str:
    stock_cell = _build_stock_link(row.name, row.code4, "technical", detail_url_builder)
    values = (
        f"{row.tag} {row.tag_label}",
        stock_cell,
        str(row.fundamental_score),
        _fmt_optional_int(row.quality_score),
        f"{row.technical_rank} {row.technical_rank_label}",
        f"{_fmt_price(row.latest)}円",
        _fmt_pct(row.dev25_pct),
        _fmt_pct(row.vwap_diff_pct),
        _fmt_position(row.day_close_position),
        _fmt_pct_unsigned(row.volume_vs_avg20_pct),
        _fmt_optional_int(row.collapse_risk_score),
        _fmt_resistance_upside(row.resistance_upside_pct),
        " / ".join(row.reasons),
    )
    cells = (
        f"<td>{escape(values[0])}</td>"
        f"<td>{stock_cell}</td>"
        + "".join(f"<td>{escape(value)}</td>" for value in values[2:])
    )
    return f"<tr>{cells}</tr>"


def _build_stock_link(
    name: str,
    code4: str,
    mode: str,
    detail_url_builder: DetailUrlBuilder | None,
) -> str:
    label = f"{escape(name)}({escape(code4)})"
    if detail_url_builder is None:
        return label
    href = escape(detail_url_builder(code4, mode), quote=True)
    return f'<a href="{href}">{label}</a>'


def _build_skipped_html(table: HybridSummaryTable) -> str:
    if not table.skipped:
        return ""
    rows = "".join(
        f"<li>{escape(item.name)}({escape(item.code4)}): {escape(item.reason)}</li>"
        for item in table.skipped
    )
    return f'<p class="summary-skipped">以下の銘柄はサマリに含まれませんでした:</p><ul class="summary-skipped-list">{rows}</ul>'


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


__all__ = ["build_hybrid_summary_html"]

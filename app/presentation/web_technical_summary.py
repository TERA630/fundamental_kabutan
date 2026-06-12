"""Web presentation helper for technical summary display."""

from __future__ import annotations

from html import escape

from app.domain.builders.technical_summary import (
    _fmt_atr,
    _fmt_bool,
    _fmt_current,
    _fmt_day_range,
    _fmt_dev25,
    _fmt_lines,
    _fmt_pct,
    _fmt_pct_unsigned,
    _fmt_position,
    _fmt_vwap,
)
from app.domain.models.technical_summary import TechnicalSummaryRow, TechnicalSummaryTable
from app.domain.policies.technical_summary import RANK_LABELS, RANK_ORDER


def build_technical_summary_html(table: TechnicalSummaryTable) -> str:
    sections = [
        '<section class="output-block summary-output technical-summary-output">',
        "<h2>Technical Summary</h2>",
    ]
    if table.rows:
        sections.append("<h3>冒頭短評</h3>")
        sections.append('<div class="table-scroll">')
        sections.append('<table class="fundamental-table summary-table technical-summary-headline-table">')
        sections.append("<thead><tr><th>銘柄</th><th>短評</th></tr></thead><tbody>")
        sections.extend(_build_headline_row_html(row) for row in table.rows)
        sections.append("</tbody></table></div>")
    for rank in RANK_ORDER:
        rows = [row for row in table.rows if row.rank == rank]
        if not rows:
            continue
        sections.append(f'<h3 class="summary-rank-heading">{rank} {escape(RANK_LABELS[rank])}</h3>')
        sections.append('<div class="table-scroll">')
        sections.append('<table class="fundamental-table summary-table technical-summary-table">')
        sections.append(
            "<thead><tr>"
            "<th>銘柄</th><th>現在値</th><th>3日騰落</th><th>当日レンジ</th><th>VWAP</th>"
            "<th>25ME dev</th><th>出来高比</th><th>前日VWAP維持</th>"
            "<th>支持線</th><th>抵抗線</th><th>60D Pos</th>"
            "</tr></thead><tbody>"
        )
        sections.extend(_build_row_html(row) for row in rows)
        sections.append("</tbody></table></div>")
    sections.append(_build_skipped_html(table))
    sections.append("</section>")
    return "".join(sections)


def _build_row_html(row: TechnicalSummaryRow) -> str:
    values = (
        f"{row.name}({row.code4})",
        _fmt_current(row),
        _fmt_pct(row.three_session_change_pct),
        _fmt_day_range(row),
        _fmt_vwap(row),
        _fmt_dev25(row),
        _fmt_pct_unsigned(row.volume_vs_avg20_pct),
        _fmt_bool(row.previous_vwap_maintained),
        _fmt_lines(row.support_lines),
        _fmt_lines(row.resistance_lines),
        _fmt_position(row.recent60_range_position),
    )
    cells = "".join(f"<td>{escape(value)}</td>" for value in values)
    return f"<tr>{cells}</tr>"


def _build_headline_row_html(row: TechnicalSummaryRow) -> str:
    values = (
        f"{row.name}({row.code4})",
        f"{row.rank} {row.rank_label}｜{row.headline_comment or 'N/A'}｜{row.next_action or 'N/A'}",
    )
    cells = "".join(f"<td>{escape(value)}</td>" for value in values)
    return f"<tr>{cells}</tr>"


def _build_skipped_html(table: TechnicalSummaryTable) -> str:
    if not table.skipped:
        return ""
    rows = "".join(
        f"<li>{escape(item.name)}({escape(item.code4)}): {escape(item.reason)}</li>"
        for item in table.skipped
    )
    return f'<p class="summary-skipped">以下の銘柄はサマリに含まれませんでした:</p><ul class="summary-skipped-list">{rows}</ul>'


__all__ = ["build_technical_summary_html"]

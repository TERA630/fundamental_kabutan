"""Web presentation helper for technical summary display."""

from __future__ import annotations

from html import escape
from typing import Callable

from app.domain.builders.technical_summary import (
    _fmt_atr,
    _fmt_collapse_score,
    _fmt_current,
    _fmt_day_range,
    _fmt_dev25,
    _fmt_lines,
    _fmt_market_price,
    _fmt_pct,
    _fmt_pct_unsigned,
    _fmt_position,
    _fmt_rsi,
    _fmt_vwap,
)
from app.domain.models.technical_summary import TechnicalSummaryRow, TechnicalSummaryTable
from app.domain.models.us_market_summary import UsMarketSummaryRow, UsMarketSummaryTable
from app.domain.policies.technical_summary import RANK_LABELS, RANK_ORDER


DetailUrlBuilder = Callable[[str, str], str]


def build_technical_summary_html(
    table: TechnicalSummaryTable,
    detail_url_builder: DetailUrlBuilder | None = None,
) -> str:
    sections = [
        '<section class="output-block summary-output technical-summary-output">',
        "<h2>Technical Summary</h2>",
    ]
    if table.us_market is not None:
        sections.append(_build_us_market_html(table.us_market))
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
            "<th>25ME dev</th><th>出来高比</th><th>崩れスコア</th>"
            "<th>支持線</th><th>抵抗線</th><th>60D Pos</th>"
            "</tr></thead><tbody>"
        )
        sections.extend(_build_row_html(row, detail_url_builder=detail_url_builder) for row in rows)
        sections.append("</tbody></table></div>")
    sections.append(_build_skipped_html(table))
    sections.append("</section>")
    return "".join(sections)


def _build_us_market_html(table: UsMarketSummaryTable) -> str:
    rows = "".join(_build_us_market_row_html(row) for row in table.rows)
    if not rows:
        rows = "<tr><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td><td>N/A</td></tr>"
    skipped = ""
    if table.skipped:
        skipped_rows = "".join(
            f"<li>{escape(item.name)}({escape(item.ticker)}): {escape(item.reason)}</li>"
            for item in table.skipped
        )
        skipped = f'<ul class="summary-skipped-list">{skipped_rows}</ul>'
    return (
        f'<h3 class="summary-rank-heading">US Market {escape(table.as_of.strftime("%Y-%m-%d %H:%M"))}</h3>'
        '<div class="table-scroll">'
        '<table class="fundamental-table summary-table technical-summary-table">'
        "<thead><tr>"
        "<th>指標/銘柄</th><th>直近値</th><th>前日騰落</th><th>5日乖離</th><th>25日乖離</th><th>RSI</th>"
        "</tr></thead><tbody>"
        f"{rows}"
        "</tbody></table></div>"
        f"{skipped}"
    )


def _build_us_market_row_html(row: UsMarketSummaryRow) -> str:
    values = (
        row.name,
        _fmt_market_price(row.latest),
        _fmt_pct(row.day_change_pct),
        _fmt_pct(row.dev5_pct),
        _fmt_pct(row.dev25_pct),
        _fmt_rsi(row.rsi14),
    )
    cells = "".join(f"<td>{escape(value)}</td>" for value in values)
    return f"<tr>{cells}</tr>"


def _build_row_html(row: TechnicalSummaryRow, *, detail_url_builder: DetailUrlBuilder | None) -> str:
    stock_cell = _build_stock_link(row.name, row.code4, "technical", detail_url_builder)
    values = (
        stock_cell,
        _fmt_current(row),
        _fmt_pct(row.three_session_change_pct),
        _fmt_day_range(row),
        _fmt_vwap(row),
        _fmt_dev25(row),
        _fmt_pct_unsigned(row.volume_vs_avg20_pct),
        _fmt_collapse_score(row.collapse_risk_score),
        _fmt_lines(row.support_lines),
        _fmt_lines(row.resistance_lines),
        _fmt_position(row.recent60_range_position),
    )
    cells = f"<td>{stock_cell}</td>" + "".join(f"<td>{escape(value)}</td>" for value in values[1:])
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


def _build_skipped_html(table: TechnicalSummaryTable) -> str:
    if not table.skipped:
        return ""
    rows = "".join(
        f"<li>{escape(item.name)}({escape(item.code4)}): {escape(item.reason)}</li>"
        for item in table.skipped
    )
    return f'<p class="summary-skipped">以下の銘柄はサマリに含まれませんでした:</p><ul class="summary-skipped-list">{rows}</ul>'


__all__ = ["build_technical_summary_html"]

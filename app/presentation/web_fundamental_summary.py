"""Web presentation helper for fundamental summary display."""

from __future__ import annotations

import html

from app.domain.models.fundamental_summary import FundamentalSummaryRow, FundamentalSummaryTable


TABLE_HEADERS = (
    "銘柄名(銘柄コード)",
    "総合スコア",
    "Quality",
    "Growth",
    "Valuation",
    "営業利益率",
    "営業利益3年CAGR",
    "ROIC",
    "Cash conversion",
    "PER",
    "投資率",
)


def build_fundamental_summary_html(table: FundamentalSummaryTable) -> str:
    rows_html = "\n".join(_build_row_html(row) for row in table.rows) or '<tr><td colspan="11">N/A</td></tr>'
    skipped_html = _build_skipped_html(table)
    return (
        '<section class="output-block summary-output">'
        '<h2>Fundamental Summary</h2>'
        '<div class="table-scroll">'
        '<table class="fundamental-table summary-table">'
        '<thead><tr>'
        + "".join(f'<th scope="col">{header}</th>' for header in TABLE_HEADERS)
        + "</tr></thead>"
        + "<tbody>"
        + rows_html
        + "</tbody>"
        + "</table>"
        + "</div>"
        + skipped_html
        + "</section>"
    )


def _build_row_html(row: FundamentalSummaryRow) -> str:
    return (
        "<tr>"
        f"<th scope=\"row\">{html.escape(row.name)} ({html.escape(row.code4)})</th>"
        f"<td>{row.total_score}</td>"
        f"<td>{_format_optional_int(row.quality_score)}</td>"
        f"<td>{_format_optional_int(row.growth_score)}</td>"
        f"<td>{_format_optional_int(row.valuation_score)}</td>"
        f"<td>{_format_percent(row.operating_margin)}</td>"
        f"<td>{_format_percent(row.operating_profit_cagr_3y)}</td>"
        f"<td>{_format_percent(row.roic)}</td>"
        f"<td>{_format_ratio(row.cash_conversion)}</td>"
        f"<td>{_format_per(row.per)}</td>"
        f"<td>{_format_percent(row.investment_rate)}</td>"
        "</tr>"
    )


def _build_skipped_html(table: FundamentalSummaryTable) -> str:
    if not table.skipped:
        return ""
    rows = "".join(
        f"<li>{html.escape(skipped.name)} ({html.escape(skipped.code4)}): {html.escape(skipped.reason)}</li>"
        for skipped in table.skipped
    )
    return f"<p class=\"summary-skipped\">以下の銘柄はサマリに含まれませんでした:</p><ul class=\"summary-skipped-list\">{rows}</ul>"


def _format_optional_int(value: int | None) -> str:
    return "N/A" if value is None else str(value)


def _format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def _format_per(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}倍"


def _format_ratio(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"

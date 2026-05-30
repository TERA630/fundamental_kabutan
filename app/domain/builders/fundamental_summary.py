"""Markdown builder for watchlist-level fundamental summary."""

from __future__ import annotations

from app.domain.models.fundamental_summary import FundamentalSummaryRow, FundamentalSummaryTable


def build_fundamental_summary_markdown(table: FundamentalSummaryTable) -> str:
    lines = [
        "# Fundamental Summary",
        "",
        "|銘柄名(銘柄コード)|総合スコア|Quality|Growth|Valuation|営業利益率|営業利益3年CAGR|ROIC|Cash conversion|PER|投資率|",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(_format_row(row) for row in table.rows)
    return "\n".join(lines) + "\n"


def _format_row(row: FundamentalSummaryRow) -> str:
    stock_label = f"{row.name} ({row.code4})"
    return (
        f"|{stock_label}"
        f"|{row.total_score}"
        f"|{_format_optional_int(row.quality_score)}"
        f"|{_format_optional_int(row.growth_score)}"
        f"|{_format_optional_int(row.valuation_score)}"
        f"|{_format_percent(row.operating_margin)}"
        f"|{_format_percent(row.operating_profit_cagr_3y)}"
        f"|{_format_percent(row.roic)}"
        f"|{_format_ratio(row.cash_conversion)}"
        f"|{_format_per(row.per)}"
        f"|{_format_percent(row.investment_rate)}|"
    )


def _format_optional_int(value: int | None) -> str:
    return "N/A" if value is None else str(value)


def _format_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}%"


def _format_per(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1f}倍"


def _format_ratio(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


__all__ = ["build_fundamental_summary_markdown"]

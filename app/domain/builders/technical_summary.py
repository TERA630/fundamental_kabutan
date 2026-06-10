"""Markdown builder for watchlist-level technical summary."""

from __future__ import annotations

from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryRow, TechnicalSummaryTable
from app.domain.models.us_market_summary import UsMarketSummaryRow, UsMarketSummaryTable
from app.domain.policies.technical_summary import RANK_LABELS, RANK_ORDER


def build_technical_summary_markdown(table: TechnicalSummaryTable) -> str:
    lines = ["# Technical Summary", ""]
    if table.us_market is not None:
        lines.extend(_format_us_market_table(table.us_market))
        lines.append("")
    rows_by_rank = {rank: [row for row in table.rows if row.rank == rank] for rank in RANK_ORDER}
    for rank in RANK_ORDER:
        rows = rows_by_rank[rank]
        if not rows:
            continue
        lines.extend(
            [
                f"## {rank} {RANK_LABELS[rank]}",
                "",
                "| 銘柄 | 現在値 | 3日騰落 | 当日レンジ | VWAP | 25日線乖離 | 出来高比 | 前日VWAP維持 | 支持線 | 抵抗線 | 60日レンジ |",
                "|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|",
            ]
        )
        lines.extend(_format_row(row) for row in rows)
        lines.append("")

    if table.skipped:
        lines.extend(["## Skipped", ""])
        lines.extend(f"- {item.name}({item.code4}): {item.reason}" for item in table.skipped)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _format_us_market_table(table: UsMarketSummaryTable) -> list[str]:
    lines = [
        f"## US Market {table.as_of.strftime('%Y-%m-%d %H:%M')}",
        "",
        "| 指標/銘柄 | 直近値 | 前日騰落 | 5日乖離 | 25日乖離 | RSI |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    if table.rows:
        lines.extend(_format_us_market_row(row) for row in table.rows)
    else:
        lines.append("| N/A | N/A | N/A | N/A | N/A | N/A |")
    if table.skipped:
        lines.append("")
        lines.extend(f"- {item.name}({item.ticker}): {item.reason}" for item in table.skipped)
    return lines


def _format_us_market_row(row: UsMarketSummaryRow) -> str:
    return (
        f"| {row.name} "
        f"| {_fmt_market_price(row.latest)} "
        f"| {_fmt_pct(row.day_change_pct)} "
        f"| {_fmt_pct(row.dev5_pct)} "
        f"| {_fmt_pct(row.dev25_pct)} "
        f"| {_fmt_rsi(row.rsi14)} |"
    )


def _format_row(row: TechnicalSummaryRow) -> str:
    return (
        f"| {row.name}({row.code4}) "
        f"| {_fmt_current(row)} "
        f"| {_fmt_pct(row.three_session_change_pct)} "
        f"| {_fmt_day_range(row)} "
        f"| {_fmt_vwap(row)} "
        f"| {_fmt_dev25(row)} "
        f"| {_fmt_pct_unsigned(row.volume_vs_avg20_pct)} "
        f"| {_fmt_bool(row.previous_vwap_maintained)} "
        f"| {_fmt_lines(row.support_lines)} "
        f"| {_fmt_resistance_lines(row.resistance_lines)} "
        f"| {_fmt_position(row.recent60_range_position)} |"
    )


def _fmt_current(row: TechnicalSummaryRow) -> str:
    return f"{_fmt_price(row.latest)}円({_fmt_pct(row.day_change_pct)})"


def _fmt_day_range(row: TechnicalSummaryRow) -> str:
    return f"{_fmt_price(row.day_high)}-{_fmt_price(row.day_low)}(値幅{_fmt_pct_unsigned_1(row.day_range_pct)}/{_fmt_atr(row.day_range_atr)})"


def _fmt_dev25(row: TechnicalSummaryRow) -> str:
    return f"{_fmt_pct(row.dev25_pct)}({_fmt_atr(row.ma25_distance_atr)})"


def _fmt_vwap(row: TechnicalSummaryRow) -> str:
    return f"{_fmt_price(row.vwap)}円({_fmt_pct(row.vwap_diff_pct)})"


def _fmt_lines(lines: tuple[TechnicalSummaryLine, ...]) -> str:
    if not lines:
        return "N/A"
    return "->".join(f"{line.label}:{_fmt_price(line.price)}" for line in lines)


def _fmt_resistance_lines(lines: tuple[TechnicalSummaryLine, ...]) -> str:
    if not lines:
        return "N/A"
    return " / ".join(f"R{index}:{line.label} {_fmt_price(line.price)}" for index, line in enumerate(lines, start=1))


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return "N/A"
    return "○" if value else "×"


def _fmt_price(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.0f}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.1f}%"


def _fmt_pct_unsigned(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.0f}%"


def _fmt_pct_unsigned_1(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _fmt_atr(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}ATR"


def _fmt_position(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def _fmt_market_price(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.2f}"


def _fmt_rsi(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"


__all__ = ["build_technical_summary_markdown"]

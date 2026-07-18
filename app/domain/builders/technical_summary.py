"""Markdown builder for watchlist-level technical summary."""

from __future__ import annotations

from app.domain.models.sector_breadth import SectorBreadthRatio, SectorBreadthRow, SectorBreadthTable
from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryRow, TechnicalSummaryTable
from app.domain.models.us_market_summary import UsMarketSummaryRow, UsMarketSummaryTable
from app.domain.policies.technical_summary import RANK_LABELS, RANK_ORDER


def build_technical_summary_markdown(table: TechnicalSummaryTable) -> str:
    lines = ["# Technical Summary", ""]
    if table.us_market is not None:
        lines.extend(_format_us_market_table(table.us_market))
        lines.append("")
    if table.sector_breadth is not None and table.sector_breadth.rows:
        lines.extend(_format_sector_breadth_table(table.sector_breadth))
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
                "| 銘柄 | 現在値 | 3日騰落 | 当日レンジ | VWAP | 25ME dev | テクニカル状態 | 1Y位置評価 | 出来高比 | 崩れスコア | 支持線 | 抵抗線 | 60日レンジ |",
                "|---|---:|---:|---:|---:|---:|---|---|---:|---|---|---|---:|",
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


def _format_sector_breadth_table(table: SectorBreadthTable) -> list[str]:
    lines = [
        "## Sector Breadth",
        "",
        "| セクター | 判定 | VWAP上 | 終端中央値 | 25日線上 | 崩れ中央値 | 出来高比中央値 | コメント |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    lines.extend(_format_sector_breadth_row(row) for row in table.rows)
    return lines


def _format_sector_breadth_row(row: SectorBreadthRow) -> str:
    return (
        f"| {row.sector} "
        f"| {row.judgement} "
        f"| {_fmt_breadth_ratio(row.vwap_above)} "
        f"| {_fmt_position(row.terminal_position_median)} "
        f"| {_fmt_breadth_ratio(row.ma25_above)} "
        f"| {_fmt_median(row.collapse_score_median)} "
        f"| {_fmt_pct_unsigned(row.volume_vs_avg20_median_pct)} "
        f"| {row.comment} |"
    )


def _format_row(row: TechnicalSummaryRow) -> str:
    return (
        f"| {row.name}({row.code4}) "
        f"| {_fmt_current(row)} "
        f"| {_fmt_pct(row.three_session_change_pct)} "
        f"| {_fmt_day_range(row)} "
        f"| {_fmt_vwap(row)} "
        f"| {_fmt_dev25(row)} "
        f"| {_fmt_technical_state(row)} "
        f"| {row.next_action or 'N/A'} "
        f"| {_fmt_pct_unsigned(row.volume_vs_avg20_pct)} "
        f"| {_fmt_collapse_score(row.collapse_risk_score)} "
        f"| {_fmt_lines(row.support_lines)} "
        f"| {_fmt_resistance_lines(row.resistance_lines)} "
        f"| {_fmt_position(row.recent60_range_position)} |"
    )


def _fmt_current(row: TechnicalSummaryRow) -> str:
    return f"{_fmt_price(row.latest)}円({_fmt_pct(row.day_change_pct)})"


def _fmt_day_range(row: TechnicalSummaryRow) -> str:
    return f"{_fmt_price(row.day_low)}-{_fmt_price(row.day_high)}円(終端:{_fmt_terminal_position(row.day_close_position)}:値幅{_fmt_atr(row.day_range_atr)})"


def _fmt_dev25(row: TechnicalSummaryRow) -> str:
    position = f" / {row.ma25_position_label}" if row.ma25_position_label else ""
    return f"{_fmt_pct(row.dev25_pct)}({_fmt_atr(row.ma25_distance_atr)}){position}"


def _fmt_technical_state(row: TechnicalSummaryRow) -> str:
    labels = []
    if row.collapse_state_label not in {None, "崩れ条件なし"}:
        labels.append(row.collapse_state_label)
    if row.reversal_state_label:
        labels.append(row.reversal_state_label)
    return " / ".join(labels) if labels else "N/A"


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


def _fmt_collapse_score(value: int | None) -> str:
    if value is None:
        return "N/A"
    return str(value)


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


def _fmt_terminal_position(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{int(value * 100)}%"


def _fmt_atr(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}ATR"


def _fmt_position(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def _fmt_breadth_ratio(value: SectorBreadthRatio) -> str:
    if value.ratio is None:
        return "N/A"
    return f"{value.count}/{value.total} {value.ratio * 100:.0f}%"


def _fmt_median(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}"


def _fmt_market_price(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.2f}"


def _fmt_rsi(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"


__all__ = ["build_technical_summary_markdown"]

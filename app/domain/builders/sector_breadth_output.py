"""Text builder for per-stock sector breadth context."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.models.sector_breadth import SectorBreadthRatio, SectorBreadthTable


def build_single_stock_sector_breadth_text(
    table: SectorBreadthTable | None,
    sectors: Iterable[str],
) -> str:
    if table is None:
        return ""
    sector_order = tuple(dict.fromkeys(sectors))
    rows_by_sector = {row.sector: row for row in table.rows}
    lines: list[str] = []
    for sector in sector_order:
        row = rows_by_sector.get(sector)
        if row is None:
            continue
        lines.extend(
            [
                f"{row.sector}：{row.judgement}",
                (
                    f"　VWAP上 {_fmt_ratio(row.vwap_above)} / "
                    f"終端中央値 {_fmt_position(row.terminal_position_median)} / "
                    f"25日線上 {_fmt_ratio(row.ma25_above)} / "
                    f"崩れ中央値 {_fmt_median(row.collapse_score_median)} / "
                    f"出来高比中央値 {_fmt_pct_unsigned(row.volume_vs_avg20_median_pct)}"
                ),
                f"　コメント：{row.comment}",
            ]
        )
    if not lines:
        return ""
    return "\n".join(["■セクター地合", *lines])


def _fmt_ratio(value: SectorBreadthRatio) -> str:
    if value.ratio is None:
        return "N/A"
    return f"{value.count}/{value.total} {value.ratio * 100:.0f}%"


def _fmt_position(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.0f}%"


def _fmt_median(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}"


def _fmt_pct_unsigned(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.0f}%"


__all__ = ["build_single_stock_sector_breadth_text"]

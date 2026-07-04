"""Policies for sector breadth aggregation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from statistics import median
from typing import Any

from app.domain.models.sector_breadth import SectorBreadthRatio, SectorBreadthRow, SectorBreadthTable
from app.domain.models.technical_summary import TechnicalSummaryRow
from app.domain.models.watchlist import WatchlistEntry

SECTOR_ORDER: tuple[str, ...] = (
    "半導体材料・装置",
    "電線・電力インフラ",
    "データセンター・電源、空調",
    "電子部品・電子機器",
    "FA・機械・ロボット",
    "防衛・重工",
    "商社・資源",
    "ディフェンシブ・内需",
    "水処理・環境インフラ",
)


def build_sector_breadth_table(
    *,
    rows: Iterable[TechnicalSummaryRow],
    watchlist_entries: Iterable[WatchlistEntry],
) -> SectorBreadthTable:
    rows_by_code = {row.code4: row for row in rows}
    sector_codes: dict[str, list[str]] = defaultdict(list)
    for entry in watchlist_entries:
        row = rows_by_code.get(entry.code4)
        if row is None:
            continue
        for sector in entry.sectors:
            sector_codes[sector].append(entry.code4)

    output: list[SectorBreadthRow] = []
    ordered_sectors = [sector for sector in SECTOR_ORDER if sector in sector_codes]
    extra_sectors = sorted(sector for sector in sector_codes if sector not in SECTOR_ORDER)
    for sector in (*ordered_sectors, *extra_sectors):
        sector_rows = [rows_by_code[code4] for code4 in sector_codes[sector]]
        output.append(build_sector_breadth_row(sector, sector_rows))
    return SectorBreadthTable(rows=tuple(output))


def build_sector_breadth_row(sector: str, rows: Iterable[TechnicalSummaryRow]) -> SectorBreadthRow:
    items = tuple(rows)
    vwap_above = _ratio(
        (
            None
            if row.latest is None or row.vwap is None
            else row.latest >= row.vwap
        )
        for row in items
    )
    ma25_above = _ratio(
        None if row.dev25_pct is None else row.dev25_pct >= 0
        for row in items
    )
    terminal_position_median = _median(row.day_close_position for row in items)
    collapse_score_median = _median(row.collapse_risk_score for row in items)
    volume_vs_avg20_median_pct = _median(row.volume_vs_avg20_pct for row in items)
    volume_spike_bearish_count = sum(1 for row in items if row.volume_spike_bearish is True)
    judgement = classify_sector_breadth(
        vwap_above_ratio=vwap_above.ratio,
        terminal_position_median=terminal_position_median,
        ma25_above_ratio=ma25_above.ratio,
        collapse_score_median=collapse_score_median,
        volume_spike_bearish_count=volume_spike_bearish_count,
    )
    return SectorBreadthRow(
        sector=sector,
        judgement=judgement,
        vwap_above=vwap_above,
        terminal_position_median=terminal_position_median,
        ma25_above=ma25_above,
        collapse_score_median=collapse_score_median,
        volume_vs_avg20_median_pct=volume_vs_avg20_median_pct,
        volume_spike_bearish_count=volume_spike_bearish_count,
        comment=build_sector_breadth_comment(
            vwap_above_ratio=vwap_above.ratio,
            terminal_position_median=terminal_position_median,
            collapse_score_median=collapse_score_median,
            volume_vs_avg20_median_pct=volume_vs_avg20_median_pct,
        ),
    )


def classify_sector_breadth(
    *,
    vwap_above_ratio: float | None,
    terminal_position_median: float | None,
    ma25_above_ratio: float | None,
    collapse_score_median: float | None,
    volume_spike_bearish_count: int = 0,
) -> str:
    if (
        _lt(vwap_above_ratio, 0.30)
        and _gte(collapse_score_median, 5.0)
        and volume_spike_bearish_count >= 1
    ):
        return "崩れ地合い"
    if _gte(vwap_above_ratio, 0.70) and _gte(terminal_position_median, 0.70) and _lte(collapse_score_median, 2.0):
        return "強い上昇地合い"
    if _gte(vwap_above_ratio, 0.60) and _gte(ma25_above_ratio, 0.70) and _lte(collapse_score_median, 4.0):
        return "押し目買い優勢"
    if _lt(vwap_above_ratio, 0.40) and _lt(terminal_position_median, 0.40):
        return "戻り売り優勢"
    if _between(vwap_above_ratio, 0.40, 0.60) or _between(terminal_position_median, 0.40, 0.60):
        return "まちまち"
    return "判定不可"


def build_sector_breadth_comment(
    *,
    vwap_above_ratio: float | None,
    terminal_position_median: float | None,
    collapse_score_median: float | None,
    volume_vs_avg20_median_pct: float | None,
) -> str:
    labels = [
        classify_vwap_above_ratio(vwap_above_ratio),
        classify_terminal_position_median(terminal_position_median),
        classify_collapse_score_median(collapse_score_median),
        classify_volume_vs_avg20_median(volume_vs_avg20_median_pct),
    ]
    return " / ".join(label for label in labels if label != "N/A") or "N/A"


def classify_vwap_above_ratio(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 0.70:
        return "セクター買い優勢"
    if value >= 0.50:
        return "中立〜やや強い"
    if value >= 0.30:
        return "まちまち"
    return "セクター売り優勢"


def classify_terminal_position_median(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 0.70:
        return "高値圏維持、買い優勢"
    if value >= 0.50:
        return "反発中"
    if value >= 0.30:
        return "戻り鈍い"
    return "売り圧優勢"


def classify_collapse_score_median(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value <= 2:
        return "健全"
    if value <= 4:
        return "注意"
    if value <= 6:
        return "崩れ警戒"
    return "回避"


def classify_volume_vs_avg20_median(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 80:
        return "実需あり"
    if value >= 50:
        return "普通"
    if value >= 30:
        return "薄い"
    return "信頼度低い"


def _ratio(values: Iterable[bool | None]) -> SectorBreadthRatio:
    usable = [value for value in values if value is not None]
    total = len(usable)
    count = sum(1 for value in usable if value is True)
    return SectorBreadthRatio(count=count, total=total, ratio=None if total == 0 else count / total)


def _median(values: Iterable[Any]) -> float | None:
    numbers = [float(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return None if not numbers else float(median(numbers))


def _gte(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold


def _lte(value: float | None, threshold: float) -> bool:
    return value is not None and value <= threshold


def _lt(value: float | None, threshold: float) -> bool:
    return value is not None and value < threshold


def _between(value: float | None, low: float, high: float) -> bool:
    return value is not None and low <= value < high


__all__ = [
    "SECTOR_ORDER",
    "build_sector_breadth_comment",
    "build_sector_breadth_row",
    "build_sector_breadth_table",
    "classify_collapse_score_median",
    "classify_sector_breadth",
    "classify_terminal_position_median",
    "classify_volume_vs_avg20_median",
    "classify_vwap_above_ratio",
]

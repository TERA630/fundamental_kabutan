"""Domain models for technical analysis snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TrendLabel = Literal["上昇トレンド", "下落トレンド", "もみ合い / 戻り局面", "N/A"]
ClosePositionLabel = Literal["高値圏で終了", "中段で終了", "安値圏で終了", "N/A"]
RangePositionLabel = Literal["高値圏", "中段", "安値圏", "N/A"]
RangeAtrLabel = Literal["浅い値幅", "通常値幅", "大きめ", "急拡大", "N/A"]
CandleLabel = Literal["陽線", "陰線", "十字線"]
WickShapeLabel = Literal["小動き", "実体大きめ", "下ヒゲ長め", "上ヒゲ長め", "小動き・十字線気味", "通常足"]
CandleBodyLabel = Literal["大陽線", "大陰線", "陽線", "陰線", "小陽線", "小陰線", "十字", "N/A"]
PreviousWickLabel = Literal["上髭", "下髭", "", "N/A"]
PullbackLabel = Literal["崩れ", "押し", "中立", "判定不可"]


@dataclass(frozen=True)
class TechnicalPriceSnapshot:
    latest: float | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    prev_close: float | None
    volume: float | None
    volume_avg20: float | None
    volume_vs_previous_pct: float | None
    day_change_price: float | None
    day_change_pct: float | None


@dataclass(frozen=True)
class TechnicalMovingAverageSnapshot:
    ma25: float | None
    ma75: float | None
    ma25_prev5: float | None
    dev25_pct: float | None
    ma25_distance: float | None
    ma25_distance_atr: float | None


@dataclass(frozen=True)
class TechnicalRangeSnapshot:
    atr14: float | None
    day_range: float | None
    day_range_atr: float | None
    day_range_label: RangeAtrLabel
    day_close_position: float | None
    day_close_position_label: ClosePositionLabel


@dataclass(frozen=True)
class PreviousSessionSnapshot:
    prev_high: float | None
    prev_low: float | None
    prev_change_pct: float | None
    prev_range: float | None
    prev_range_atr: float | None
    prev_close_position: float | None
    prev_volume_vs_avg20_pct: float | None
    prev_volume_change_pct: float | None
    prev_high_higher: bool | None
    prev_low_higher: bool | None
    candle_body_label: CandleBodyLabel
    wick_label: PreviousWickLabel
    candle: CandleLabel
    wick_shape: WickShapeLabel
    pullback: PullbackLabel


@dataclass(frozen=True)
class BreaklineSnapshot:
    recent5_high: float | None
    recent5_low: float | None
    recent20_high: float | None
    recent20_low: float | None
    recent60_high: float | None
    recent60_low: float | None
    recent5_high_distance: float | None
    recent5_low_distance: float | None
    recent20_high_distance: float | None
    recent20_low_distance: float | None
    recent60_high_distance: float | None
    recent60_low_distance: float | None
    recent5_high_distance_pct: float | None
    recent5_low_distance_pct: float | None
    recent20_high_distance_pct: float | None
    recent20_low_distance_pct: float | None
    recent60_high_distance_pct: float | None
    recent60_low_distance_pct: float | None
    recent60_range_position: float | None
    recent60_range_position_label: RangePositionLabel


@dataclass(frozen=True)
class TechnicalSnapshot:
    price: TechnicalPriceSnapshot
    moving_average: TechnicalMovingAverageSnapshot
    range: TechnicalRangeSnapshot
    previous_session: PreviousSessionSnapshot
    breakline: BreaklineSnapshot
    rsi14: float | None
    trend: TrendLabel


__all__ = [
    "BreaklineSnapshot",
    "CandleBodyLabel",
    "CandleLabel",
    "ClosePositionLabel",
    "PreviousSessionSnapshot",
    "PreviousWickLabel",
    "PullbackLabel",
    "RangeAtrLabel",
    "RangePositionLabel",
    "TechnicalMovingAverageSnapshot",
    "TechnicalPriceSnapshot",
    "TechnicalRangeSnapshot",
    "TechnicalSnapshot",
    "TrendLabel",
    "WickShapeLabel",
]

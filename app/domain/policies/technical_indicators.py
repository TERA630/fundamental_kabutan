"""Domain policies for daily technical indicators."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.domain.models.technical_snapshot import (
    BreaklineSnapshot,
    CandleLabel,
    ClosePositionLabel,
    PreviousSessionSnapshot,
    PullbackLabel,
    RangeAtrLabel,
    RangePositionLabel,
    TechnicalMovingAverageSnapshot,
    TechnicalPriceSnapshot,
    TechnicalRangeSnapshot,
    TechnicalSnapshot,
    TrendLabel,
    WickShapeLabel,
)

REQUIRED_DAILY_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


def _none_if_nan(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _pct_change(current: float | int | None, previous: float | int | None) -> float | None:
    ratio = _safe_div(current, previous)
    if ratio is None:
        return None
    return (ratio - 1) * 100


def normalize_daily_history(history: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_DAILY_COLUMNS if column not in history.columns]
    if missing:
        raise ValueError(f"日足価格データに必要な列がありません: {', '.join(missing)}")
    out = history.loc[:, REQUIRED_DAILY_COLUMNS].copy()
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    return out


def calc_moving_averages(history: pd.DataFrame) -> pd.DataFrame:
    out = history.copy()
    close = out["Close"]
    out["ma5"] = close.rolling(5).mean()
    out["ma25"] = close.rolling(25).mean()
    out["ma25_prev5"] = out["ma25"].shift(5)
    out["dev5_pct"] = ((close / out["ma5"]) - 1) * 100
    out["dev25_pct"] = ((close / out["ma25"]) - 1) * 100
    return out


def calc_rsi14(close: pd.Series) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    return 100 - 100 / (1 + avg_gain / avg_loss)


def calc_atr14(history: pd.DataFrame) -> pd.Series:
    high = history["High"]
    low = history["Low"]
    prev_close = history["Close"].shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()


def label_range_atr(value: float | None) -> RangeAtrLabel:
    if value is None:
        return "N/A"
    if value < 0.5:
        return "浅い値幅"
    if value < 1.0:
        return "通常値幅"
    if value < 1.5:
        return "大きめ"
    return "急拡大"


def label_close_position(value: float | None) -> ClosePositionLabel:
    if value is None:
        return "N/A"
    if value >= 0.60:
        return "高値圏で終了"
    if value >= 0.30:
        return "中段で終了"
    return "安値圏で終了"


def label_range_position(value: float | None) -> RangePositionLabel:
    if value is None:
        return "N/A"
    if value >= 0.60:
        return "高値圏"
    if value >= 0.30:
        return "中段"
    return "安値圏"


def label_trend(latest: float | None, ma5: float | None, ma25: float | None, ma25_prev5: float | None) -> TrendLabel:
    if latest is None or ma5 is None or ma25 is None:
        return "N/A"
    if ma25_prev5 is not None and latest > ma5 > ma25 and ma25 > ma25_prev5:
        return "上昇トレンド"
    if latest < ma5 < ma25:
        return "下落トレンド"
    return "もみ合い / 戻り局面"


def label_candle(open_value: float | None, close_value: float | None) -> CandleLabel:
    if open_value is not None and close_value is not None:
        if close_value > open_value:
            return "陽線"
        if close_value < open_value:
            return "陰線"
    return "十字線"


def label_wick_shape(open_value: float | None, high: float | None, low: float | None, close: float | None) -> WickShapeLabel:
    if None in (open_value, high, low, close):
        return "小動き"
    day_range = high - low
    if day_range <= 0:
        return "小動き"
    body = abs(close - open_value)
    upper_wick = high - max(open_value, close)
    lower_wick = min(open_value, close) - low
    if body / day_range >= 0.65:
        return "実体大きめ"
    if lower_wick / day_range >= 0.40 and lower_wick >= body * 1.5:
        return "下ヒゲ長め"
    if upper_wick / day_range >= 0.40 and upper_wick >= body * 1.5:
        return "上ヒゲ長め"
    if body / day_range <= 0.20:
        return "小動き・十字線気味"
    return "通常足"


def label_pullback(prev_range_atr: float | None, prev_close_position: float | None, prev_vol_ratio: float | None) -> PullbackLabel:
    if prev_range_atr is None or prev_close_position is None:
        return "判定不可"
    volume_ratio = prev_vol_ratio if prev_vol_ratio is not None else 0.0
    if prev_range_atr >= 1.30 and prev_close_position <= 0.30 and volume_ratio >= 20:
        return "崩れ"
    if prev_range_atr >= 1.50 and prev_close_position <= 0.40:
        return "崩れ"
    if 0.50 <= prev_range_atr <= 1.20 and prev_close_position >= 0.45 and volume_ratio <= 20:
        return "押し"
    return "中立"


def build_technical_snapshot(history: pd.DataFrame) -> TechnicalSnapshot:
    daily = normalize_daily_history(history)
    if len(daily) < 30:
        raise ValueError("日足価格データが不足しています: 30件以上必要です")

    enriched = calc_moving_averages(daily)
    enriched["rsi14"] = calc_rsi14(enriched["Close"])
    enriched["atr14"] = calc_atr14(enriched)
    enriched["volume_avg20"] = enriched["Volume"].rolling(20).mean()

    latest_row = enriched.iloc[-1]
    prev_row = enriched.iloc[-2]
    prev_prev_row = enriched.iloc[-3] if len(enriched) >= 3 else None

    latest = _none_if_nan(latest_row["Close"])
    open_value = _none_if_nan(latest_row["Open"])
    high = _none_if_nan(latest_row["High"])
    low = _none_if_nan(latest_row["Low"])
    volume = _none_if_nan(latest_row["Volume"])
    volume_avg20 = _none_if_nan(latest_row["volume_avg20"])
    prev_close = _none_if_nan(prev_row["Close"])
    atr14 = _none_if_nan(latest_row["atr14"])
    ma5 = _none_if_nan(latest_row["ma5"])
    ma25 = _none_if_nan(latest_row["ma25"])
    ma25_prev5 = _none_if_nan(latest_row["ma25_prev5"])

    day_range = (high - low) if high is not None and low is not None else None
    day_close_position = _safe_div(latest - low, day_range) if latest is not None and low is not None else None
    ma25_distance = latest - ma25 if latest is not None and ma25 is not None else None

    prev_high = _none_if_nan(prev_row["High"])
    prev_low = _none_if_nan(prev_row["Low"])
    prev_open = _none_if_nan(prev_row["Open"])
    prev_volume = _none_if_nan(prev_row["Volume"])
    prev_volume_avg20 = _none_if_nan(enriched["Volume"].shift(1).rolling(20).mean().iloc[-1])
    prev_prev_close = _none_if_nan(prev_prev_row["Close"]) if prev_prev_row is not None else None
    prev_range = (prev_high - prev_low) if prev_high is not None and prev_low is not None else None
    prev_close_position = _safe_div(prev_close - prev_low, prev_range) if prev_close is not None and prev_low is not None else None
    prev_vol_ratio = _pct_change(prev_volume, prev_volume_avg20)

    shifted = enriched.shift(1)
    recent5_high = _none_if_nan(shifted["High"].rolling(5).max().iloc[-1])
    recent5_low = _none_if_nan(shifted["Low"].rolling(5).min().iloc[-1])
    recent20_high = _none_if_nan(shifted["High"].rolling(20).max().iloc[-1])
    recent20_low = _none_if_nan(shifted["Low"].rolling(20).min().iloc[-1])
    recent60_high = _none_if_nan(shifted["High"].rolling(60).max().iloc[-1])
    recent60_low = _none_if_nan(shifted["Low"].rolling(60).min().iloc[-1])
    recent60_width = recent60_high - recent60_low if recent60_high is not None and recent60_low is not None else None
    recent60_range_position = _safe_div(latest - recent60_low, recent60_width) if latest is not None and recent60_low is not None else None

    price = TechnicalPriceSnapshot(
        latest=latest,
        open=open_value,
        high=high,
        low=low,
        close=latest,
        prev_close=prev_close,
        volume=volume,
        volume_avg20=volume_avg20,
        day_change_price=latest - prev_close if latest is not None and prev_close is not None else None,
        day_change_pct=_pct_change(latest, prev_close),
    )
    moving_average = TechnicalMovingAverageSnapshot(
        ma5=ma5,
        ma25=ma25,
        ma25_prev5=ma25_prev5,
        dev5_pct=_none_if_nan(latest_row["dev5_pct"]),
        dev25_pct=_none_if_nan(latest_row["dev25_pct"]),
        ma25_distance=ma25_distance,
        ma25_distance_atr=_safe_div(ma25_distance, atr14),
    )
    range_snapshot = TechnicalRangeSnapshot(
        atr14=atr14,
        day_range=day_range,
        day_range_atr=_safe_div(day_range, atr14),
        day_range_label=label_range_atr(_safe_div(day_range, atr14)),
        day_close_position=day_close_position,
        day_close_position_label=label_close_position(day_close_position),
    )
    previous_session = PreviousSessionSnapshot(
        prev_high=prev_high,
        prev_low=prev_low,
        prev_change_pct=_pct_change(prev_close, prev_prev_close),
        prev_range=prev_range,
        prev_range_atr=_safe_div(prev_range, atr14),
        prev_close_position=prev_close_position,
        prev_volume_vs_avg20_pct=prev_vol_ratio,
        candle=label_candle(prev_open, prev_close),
        wick_shape=label_wick_shape(prev_open, prev_high, prev_low, prev_close),
        pullback=label_pullback(_safe_div(prev_range, atr14), prev_close_position, prev_vol_ratio),
    )
    breakline = BreaklineSnapshot(
        recent5_high=recent5_high,
        recent5_low=recent5_low,
        recent20_high=recent20_high,
        recent20_low=recent20_low,
        recent60_high=recent60_high,
        recent60_low=recent60_low,
        recent5_high_distance=latest - recent5_high if latest is not None and recent5_high is not None else None,
        recent5_low_distance=latest - recent5_low if latest is not None and recent5_low is not None else None,
        recent20_high_distance=latest - recent20_high if latest is not None and recent20_high is not None else None,
        recent20_low_distance=latest - recent20_low if latest is not None and recent20_low is not None else None,
        recent60_high_distance=latest - recent60_high if latest is not None and recent60_high is not None else None,
        recent60_low_distance=latest - recent60_low if latest is not None and recent60_low is not None else None,
        recent5_high_distance_pct=_pct_change(latest, recent5_high),
        recent5_low_distance_pct=_pct_change(latest, recent5_low),
        recent20_high_distance_pct=_pct_change(latest, recent20_high),
        recent20_low_distance_pct=_pct_change(latest, recent20_low),
        recent60_high_distance_pct=_pct_change(latest, recent60_high),
        recent60_low_distance_pct=_pct_change(latest, recent60_low),
        recent60_range_position=recent60_range_position,
        recent60_range_position_label=label_range_position(recent60_range_position),
    )
    return TechnicalSnapshot(
        price=price,
        moving_average=moving_average,
        range=range_snapshot,
        previous_session=previous_session,
        breakline=breakline,
        rsi14=_none_if_nan(latest_row["rsi14"]),
        trend=label_trend(latest, ma5, ma25, ma25_prev5),
    )


__all__ = [
    "REQUIRED_DAILY_COLUMNS",
    "build_technical_snapshot",
    "calc_atr14",
    "calc_moving_averages",
    "calc_rsi14",
    "label_candle",
    "label_close_position",
    "label_pullback",
    "label_range_atr",
    "label_range_position",
    "label_trend",
    "label_wick_shape",
    "normalize_daily_history",
]

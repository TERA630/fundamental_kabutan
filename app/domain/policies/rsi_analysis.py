"""Policies for 5-minute/hourly RSI labels and divergence."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from app.domain.models.rsi_analysis import RsiAnalysis, RsiDivergence, RsiSignal
from app.domain.policies.market_history import normalize_history_frame
from app.domain.policies.technical_indicators import calc_rsi14

_NO_DIVERGENCE = RsiDivergence("明確な乖離なし", "")
_NA_DIVERGENCE = RsiDivergence("N/A", "")


def build_rsi_analysis(intraday_history: pd.DataFrame) -> RsiAnalysis:
    five_min_frame = _prepare_ohlc_frame(intraday_history)
    hourly_frame = _resample_hourly(five_min_frame)

    five_min_signal = build_rsi_signal(five_min_frame["Close"] if not five_min_frame.empty else pd.Series(dtype=float))
    hourly_signal = build_rsi_signal(hourly_frame["Close"] if not hourly_frame.empty else pd.Series(dtype=float))
    five_min_divergence = build_rsi_divergence(five_min_frame)
    hourly_divergence = build_rsi_divergence(hourly_frame)

    return RsiAnalysis(
        five_min=five_min_signal,
        hourly=hourly_signal,
        five_min_divergence=five_min_divergence,
        hourly_divergence=hourly_divergence,
        overall_label=classify_rsi_overall(
            five_min_signal=five_min_signal,
            hourly_signal=hourly_signal,
            five_min_divergence=five_min_divergence,
            hourly_divergence=hourly_divergence,
        ),
    )


def build_rsi_signal(close: pd.Series) -> RsiSignal:
    close = pd.to_numeric(close, errors="coerce").dropna()
    if close.empty:
        return _na_signal()
    rsi = calc_rsi14(close).dropna()
    if len(rsi) < 4:
        return _na_signal()

    value = _safe_float(rsi.iloc[-1])
    previous = _safe_float(rsi.iloc[-4])
    if value is None or previous is None:
        return _na_signal()
    delta = value - previous
    symbol, direction = _classify_rsi_direction(delta)
    return RsiSignal(
        value=value,
        delta=delta,
        direction_symbol=symbol,
        direction_label=direction,
        level_label=classify_rsi_level(value, delta),
    )


def classify_rsi_level(value: float, delta: float) -> str:
    if value >= 75:
        return "過熱後半"
    if value >= 70:
        return "やや過熱"
    if 55 <= value < 70 and delta >= 2.0:
        return "勢い良好"
    if 45 <= value < 55 and delta >= 2.0:
        return "勢い改善"
    if value >= 60 and -2.0 < delta < 2.0:
        return "高止まり"
    if value >= 60 and delta <= -2.0:
        return "勢い鈍化"
    if 40 <= value < 55 and delta <= -2.0:
        return "反発弱い"
    if 30 <= value < 40 and delta >= 2.0:
        return "底打ち初動"
    if value < 30:
        return "売られ過ぎ"
    return "中立"


def build_rsi_divergence(frame: pd.DataFrame) -> RsiDivergence:
    ohlc = _prepare_ohlc_frame(frame)
    if len(ohlc) < 20:
        return _NA_DIVERGENCE

    rsi = calc_rsi14(ohlc["Close"])
    analysis_frame = ohlc.assign(rsi=rsi).dropna(subset=["High", "Low", "Close", "rsi"])
    if len(analysis_frame) < 7:
        return _NA_DIVERGENCE

    price_highs = _confirmed_pivots(analysis_frame["High"], "high")
    rsi_highs = _confirmed_pivots(analysis_frame["rsi"], "high")
    if len(price_highs) >= 2 and len(rsi_highs) >= 2:
        prev_price_high, last_price_high = price_highs[-2][1], price_highs[-1][1]
        prev_rsi_high, last_rsi_high = rsi_highs[-2][1], rsi_highs[-1][1]
        if last_price_high >= prev_price_high * 1.0015:
            if last_rsi_high >= prev_rsi_high + 2.0:
                return RsiDivergence("勢い追随", "価格高値更新 / RSIも更新")
            return RsiDivergence("上昇鈍化", "価格高値更新 / RSI未更新")

    price_lows = _confirmed_pivots(analysis_frame["Low"], "low")
    rsi_lows = _confirmed_pivots(analysis_frame["rsi"], "low")
    if len(price_lows) >= 2 and len(rsi_lows) >= 2:
        prev_price_low, last_price_low = price_lows[-2][1], price_lows[-1][1]
        prev_rsi_low, last_rsi_low = rsi_lows[-2][1], rsi_lows[-1][1]
        price_low_updated = last_price_low <= prev_price_low * 0.9985
        price_low_raised = last_price_low >= prev_price_low * 1.0015
        rsi_low_raised = last_rsi_low >= prev_rsi_low + 2.0
        rsi_low_declined = last_rsi_low <= prev_rsi_low - 2.0
        if price_low_updated and rsi_low_raised:
            return RsiDivergence("底打ち兆候", "価格安値更新 / RSI安値切上げ")
        if price_low_raised and rsi_low_declined:
            return RsiDivergence("反発弱い", "安値切上げ / RSI低下")
        if price_low_raised and rsi_low_raised:
            return RsiDivergence("底堅い", "安値切上げ / RSIも改善")

    return _NO_DIVERGENCE


def classify_rsi_overall(
    *,
    five_min_signal: RsiSignal,
    hourly_signal: RsiSignal,
    five_min_divergence: RsiDivergence,
    hourly_divergence: RsiDivergence,
) -> str:
    if hourly_signal.level_label == "N/A" and five_min_signal.level_label == "N/A":
        return "N/A"

    if hourly_divergence.label == "上昇鈍化":
        return "上昇鈍化警戒"
    if hourly_divergence.label == "底打ち兆候":
        return "底打ち初動"
    if hourly_divergence.label == "底堅い":
        return "底打ち初動" if _rsi_category(five_min_signal.level_label) in {"strong", "neutral"} else "勢い改善"

    hourly_category = _rsi_category(hourly_signal.level_label)
    five_min_category = _rsi_category(five_min_signal.level_label)

    if "oversold" in {hourly_category, five_min_category}:
        overall = "底打ち初動" if _has_bottoming_upgrade(five_min_signal, hourly_signal, five_min_divergence, hourly_divergence) else "底打ち確認待ち"
    elif hourly_category == "alert":
        overall = "上昇鈍化警戒"
    elif hourly_category == "strong" and five_min_category in {"strong", "neutral"}:
        overall = "勢い良好"
    elif hourly_category == "neutral" and five_min_category == "strong":
        overall = "勢い改善"
    elif hourly_category == "neutral" and five_min_category == "neutral":
        overall = "高止まり"
    elif hourly_category in {"strong", "neutral"} and five_min_category == "alert":
        overall = "短期鈍化"
    else:
        overall = "高止まり"

    if hourly_divergence.label == "勢い追随":
        overall = _strengthen_overall(overall)
    if five_min_divergence.label == "上昇鈍化":
        overall = _weaken_overall(overall)
    if five_min_divergence.label == "底打ち兆候" and hourly_category != "alert":
        overall = _strengthen_overall(overall)
    return overall


def _prepare_ohlc_frame(history: Any) -> pd.DataFrame:
    frame = normalize_history_frame(history)
    if frame.empty:
        return frame
    frame = frame[frame["Volume"].fillna(0) > 0]
    return frame.dropna(subset=["High", "Low", "Close"])


def _resample_hourly(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    hourly = frame.resample("60min", origin="start_day").agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    hourly = hourly.dropna(subset=["Open", "High", "Low", "Close"])
    return hourly[hourly["Volume"].fillna(0) > 0]


def _classify_rsi_direction(delta: float) -> tuple[Literal["↑", "↓", "→"], Literal["上昇中", "低下中", "横ばい"]]:
    if delta >= 2.0:
        return "↑", "上昇中"
    if delta <= -2.0:
        return "↓", "低下中"
    return "→", "横ばい"


def _confirmed_pivots(series: pd.Series, kind: Literal["high", "low"]) -> list[tuple[pd.Timestamp, float]]:
    values = pd.to_numeric(series, errors="coerce")
    pivots: list[tuple[pd.Timestamp, float]] = []
    for i in range(3, len(values) - 3):
        value = _safe_float(values.iloc[i])
        if value is None:
            continue
        previous = values.iloc[i - 3 : i].dropna()
        following = values.iloc[i + 1 : i + 4].dropna()
        if len(previous) < 3 or len(following) < 3:
            continue
        if kind == "high" and value > previous.max() and value > following.max():
            pivots.append((pd.Timestamp(values.index[i]), value))
        elif kind == "low" and value < previous.min() and value < following.min():
            pivots.append((pd.Timestamp(values.index[i]), value))
    return pivots


def _rsi_category(label: str) -> str:
    if label in {"勢い良好", "勢い改善", "底打ち初動", "底堅い", "勢い追随"}:
        return "strong"
    if label in {"高止まり", "中立", "明確な乖離なし"}:
        return "neutral"
    if label in {"やや過熱", "過熱後半", "勢い鈍化", "反発弱い", "上昇鈍化"}:
        return "alert"
    if label == "売られ過ぎ":
        return "oversold"
    return "unknown"


def _has_bottoming_upgrade(
    five_min_signal: RsiSignal,
    hourly_signal: RsiSignal,
    five_min_divergence: RsiDivergence,
    hourly_divergence: RsiDivergence,
) -> bool:
    return (
        five_min_signal.level_label == "底打ち初動"
        or hourly_signal.level_label == "底打ち初動"
        or five_min_divergence.label in {"底打ち兆候", "底堅い"}
        or hourly_divergence.label in {"底打ち兆候", "底堅い"}
    )


def _strengthen_overall(label: str) -> str:
    order = ["底打ち確認待ち", "短期鈍化", "高止まり", "勢い改善", "勢い良好"]
    if label == "上昇鈍化警戒":
        return label
    if label == "底打ち初動":
        return label
    if label not in order:
        return label
    return order[min(order.index(label) + 1, len(order) - 1)]


def _weaken_overall(label: str) -> str:
    order = ["底打ち確認待ち", "短期鈍化", "高止まり", "勢い改善", "勢い良好"]
    if label in {"上昇鈍化警戒", "底打ち確認待ち"}:
        return label
    if label == "底打ち初動":
        return "底打ち確認待ち"
    if label not in order:
        return label
    return order[max(order.index(label) - 1, 0)]


def _na_signal() -> RsiSignal:
    return RsiSignal(value=None, delta=None, direction_symbol="N/A", direction_label="N/A", level_label="N/A")


def _safe_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


__all__ = [
    "build_rsi_analysis",
    "build_rsi_divergence",
    "build_rsi_signal",
    "classify_rsi_level",
    "classify_rsi_overall",
]

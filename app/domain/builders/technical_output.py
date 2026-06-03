"""Builder for technical analysis text output."""

from __future__ import annotations

from app.domain.usecases.technical_analysis import TechnicalAnalysisResult


def build_technical_output(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    lines = [
        f"【銘柄】{result.name} ({result.code4})",
        _format_opening_summary(result),
        "",
        "■当日位置・レンジ",
        f"始値：{_fmt_price(snapshot.price.open)}",
        f"高値：{_fmt_price(snapshot.price.high)}",
        f"安値：{_fmt_price(snapshot.price.low)}",
        f"終値：{_fmt_price(snapshot.price.close)}",
        f"当日値幅：{_fmt_price(snapshot.range.day_range)}（ATR比 {_fmt_multiple(snapshot.range.day_range_atr)} / {snapshot.range.day_range_label}）",
        "",
        "■移動平均・出来高",
        f"5日線：{_fmt_price(snapshot.moving_average.ma5)}（乖離 {_fmt_pct(snapshot.moving_average.dev5_pct)}）",
        f"25日線：{_fmt_price(snapshot.moving_average.ma25)}（乖離 {_fmt_pct(snapshot.moving_average.dev25_pct)} / ATR比 {_fmt_multiple(snapshot.moving_average.ma25_distance_atr)}）",
        f"14日ATR：{_fmt_price(snapshot.range.atr14)}",
        f"出来高：20日平均出来高比 {_fmt_volume_ratio(snapshot.price.volume, snapshot.price.volume_avg20)}　（{_fmt_volume(snapshot.price.volume)}）",
        "",
        "■前日評価",
        f"前日騰落率：{_fmt_pct(snapshot.previous_session.prev_change_pct)}",
        "",
        f"前日Vwap維持：{_fmt_bool_mark(_is_previous_vwap_maintained(result))}",
        f"ローソク：{snapshot.previous_session.candle} / {snapshot.previous_session.wick_shape}",
        f"押し判定：{snapshot.previous_session.pullback}",
        "",
        "■支持線",
        f"前日安値：{_fmt_price(snapshot.previous_session.prev_low)}",
        f"20日安値：{_fmt_price(snapshot.breakline.recent20_low)}",
        f"60日安値：{_fmt_price(snapshot.breakline.recent60_low)}",
    ]
    return "\n".join(lines) + "\n"


def _format_opening_summary(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    vwap_snapshot = result.vwap_snapshot
    latest = snapshot.price.latest
    vwap = _as_float(vwap_snapshot.get("vwap"))
    vwap_diff = latest - vwap if latest is not None and vwap is not None else None
    vwap_diff_pct = ((latest / vwap) - 1) * 100 if latest is not None and vwap not in (None, 0) else None
    vwap_diff_atr = _safe_div(vwap_diff, snapshot.range.atr14)
    vwap_source_suffix = " (日足参考値)" if vwap_snapshot.get("vwap_source") == "日足参考値" else ""
    return "\n".join(
        [
            f"株価：{_fmt_price_current(latest)}円（前日比{_fmt_price_signed(snapshot.price.day_change_price)}円：{_fmt_pct(snapshot.price.day_change_pct)}）（当日{_short_close_position_label(snapshot.range.day_close_position_label)}{_fmt_position_pct(snapshot.range.day_close_position)}）",
            f"トレンド：{_short_trend_label(snapshot.trend)}　　　25日線傾き：{_ma25_slope_symbol(result)}",
            "",
            f"Vwap：{_fmt_price_signed(vwap_diff)}円（{_fmt_pct(vwap_diff_pct)}、{_fmt_atr_unsigned(vwap_diff_atr)}）{vwap_source_suffix}",
            f"位置：25日線 {_fmt_pct(snapshot.moving_average.dev25_pct)}（{_fmt_atr(snapshot.moving_average.ma25_distance_atr)}）",
            f"前日高値：{_fmt_price(snapshot.previous_session.prev_high)}　前日安値：{_fmt_price(snapshot.previous_session.prev_low)}　　　　{_format_previous_high_evaluation(result)}",
            f"5日高値 {_fmt_pct(snapshot.breakline.recent5_high_distance_pct)}　20日高値まで：{_fmt_high_remaining_pct(snapshot.breakline.recent20_high_distance_pct)} 　　60日レンジ位置 {_fmt_position_pct(snapshot.breakline.recent60_range_position)}（{snapshot.breakline.recent60_range_position_label}）",
            f"RSI：{_fmt_number(snapshot.rsi14)}",
        ]
    )


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _range_position(latest: float | None, low: float | None, high: float | None) -> float | None:
    width = high - low if high is not None and low is not None else None
    return _safe_div(latest - low, width) if latest is not None and low is not None else None


def _fmt_number(value: float | None, digits: int = 1) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def _fmt_price(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.2f}"


def _fmt_price_current(value: float | None) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def _fmt_price_signed(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+,.2f}"


def _fmt_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.1f}%"


def _fmt_position_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def _fmt_multiple(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}倍"


def _fmt_atr(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2f}ATR"


def _fmt_atr_unsigned(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}ATR"


def _fmt_volume(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.0f}株"


def _fmt_volume_ratio(volume: float | None, average: float | None) -> str:
    ratio = _safe_div(volume, average)
    return "N/A" if ratio is None else f"{ratio * 100:.0f}%"


def _fmt_bool_mark(value: bool | None) -> str:
    if value is None:
        return "N/A"
    return "〇" if value else "×"


def _is_previous_vwap_maintained(result: TechnicalAnalysisResult) -> bool | None:
    prev_close = result.snapshot.price.prev_close
    vwap = _as_float(result.vwap_snapshot.get("vwap"))
    if prev_close is None or vwap is None:
        return None
    return prev_close >= vwap


def _format_previous_high_evaluation(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    latest = snapshot.price.latest
    prev_high = snapshot.previous_session.prev_high
    prev_low = snapshot.previous_session.prev_low
    if latest is None or prev_high is None or prev_low is None:
        return "N/A"
    if latest > prev_high:
        return f"前日高値突破：{_fmt_pct(_pct_change(latest, prev_high))}"
    if latest >= prev_low:
        position = _range_position(latest, prev_low, prev_high)
        return f"前日レンジ：{_fmt_position_pct(position)}（{_range_position_label_middle(position)}）"
    return f"前日安値：{_fmt_pct(_pct_change(latest, prev_low))}"


def _pct_change(current: float | int | None, previous: float | int | None) -> float | None:
    ratio = _safe_div(current, previous)
    if ratio is None:
        return None
    return (ratio - 1) * 100


def _fmt_high_remaining_pct(distance_pct: float | None) -> str:
    if distance_pct is None:
        return "N/A"
    if distance_pct >= 0:
        return f"突破 {_fmt_pct(distance_pct)}"
    return f"{abs(distance_pct):.1f}%"


def _ma25_slope_symbol(result: TechnicalAnalysisResult) -> str:
    ma25 = result.snapshot.moving_average.ma25
    ma25_prev5 = result.snapshot.moving_average.ma25_prev5
    if ma25 is None or ma25_prev5 is None:
        return "N/A"
    if ma25 > ma25_prev5:
        return "↑"
    if ma25 < ma25_prev5:
        return "↓"
    return "→"


def _short_close_position_label(label: str) -> str:
    if label == "高値圏で終了":
        return "高値圏"
    if label == "中段で終了":
        return "中間"
    if label == "安値圏で終了":
        return "安値圏"
    return ""


def _range_position_label_middle(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 0.60:
        return "高値圏"
    if value >= 0.30:
        return "中間"
    return "安値圏"


def _short_trend_label(trend: str) -> str:
    if trend == "上昇トレンド":
        return "上昇"
    if trend == "下落トレンド":
        return "下落"
    if trend == "N/A":
        return "N/A"
    return "もみあい"


__all__ = ["build_technical_output"]

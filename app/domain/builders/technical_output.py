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
        f"終端位置：{_fmt_position_pct(snapshot.range.day_close_position)}（{snapshot.range.day_close_position_label}）",
        "",
        "■移動平均・出来高",
        f"5日線：{_fmt_price(snapshot.moving_average.ma5)}（乖離 {_fmt_pct(snapshot.moving_average.dev5_pct)}）",
        f"25日線：{_fmt_price(snapshot.moving_average.ma25)}（乖離 {_fmt_pct(snapshot.moving_average.dev25_pct)} / ATR比 {_fmt_multiple(snapshot.moving_average.ma25_distance_atr)}）",
        f"14日ATR：{_fmt_price(snapshot.range.atr14)}",
        f"出来高：{_fmt_volume(snapshot.price.volume)}（20日平均 {_fmt_volume(snapshot.price.volume_avg20)}）",
        "",
        "■前日評価",
        f"前日騰落率：{_fmt_pct(snapshot.previous_session.prev_change_pct)}",
        f"前日Vwap維持：{_fmt_bool_mark(_is_previous_vwap_maintained(result))}",
        f"ローソク：{snapshot.previous_session.candle} / {snapshot.previous_session.wick_shape}",
        f"押し判定：{snapshot.previous_session.pullback}",
        "",
        "■節目・ブレイクライン",
        _format_breakline_pair("5日", snapshot.breakline.recent5_high, snapshot.breakline.recent5_high_distance, snapshot.breakline.recent5_high_distance_pct, snapshot.breakline.recent5_low, snapshot.breakline.recent5_low_distance, snapshot.breakline.recent5_low_distance_pct),
        _format_breakline_pair("20日", snapshot.breakline.recent20_high, snapshot.breakline.recent20_high_distance, snapshot.breakline.recent20_high_distance_pct, snapshot.breakline.recent20_low, snapshot.breakline.recent20_low_distance, snapshot.breakline.recent20_low_distance_pct),
        _format_breakline_pair("60日", snapshot.breakline.recent60_high, snapshot.breakline.recent60_high_distance, snapshot.breakline.recent60_high_distance_pct, snapshot.breakline.recent60_low, snapshot.breakline.recent60_low_distance, snapshot.breakline.recent60_low_distance_pct),
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
    timestamp = vwap_snapshot.get("latest_price_timestamp") or "N/A"
    prev_range_position = _range_position(
        latest,
        snapshot.previous_session.prev_low,
        snapshot.previous_session.prev_high,
    )
    return "\n".join(
        [
            _fmt_timestamp(timestamp),
            f"株価：{_fmt_price_current(latest)}円（前日比{_fmt_price_signed(snapshot.price.day_change_price)}円：{_fmt_pct(snapshot.price.day_change_pct)}）（{_short_close_position_label(snapshot.range.day_close_position_label)}{_fmt_position_pct(snapshot.range.day_close_position)}）",
            f"トレンド：{_trend_symbol(snapshot.trend)}　{_short_trend_label(snapshot.trend)}",
            f"Vwap：{_fmt_price_signed(vwap_diff)}円（{_fmt_pct(vwap_diff_pct)}、{_fmt_atr_unsigned(vwap_diff_atr)}）{vwap_source_suffix}",
            f"位置：25日線 {_fmt_pct(snapshot.moving_average.dev25_pct)}（{_fmt_atr(snapshot.moving_average.ma25_distance_atr)}）",
            f"前日高値：{_fmt_price(snapshot.previous_session.prev_high)}　前日安値：{_fmt_price(snapshot.previous_session.prev_low)}　　　レンジ位置 {_fmt_position_pct(prev_range_position)}（{_range_position_label_middle(prev_range_position)}）",
            f"5日高値 {_fmt_pct(snapshot.breakline.recent5_high_distance_pct)}　60日レンジ位置 {_fmt_position_pct(snapshot.breakline.recent60_range_position)}（{snapshot.breakline.recent60_range_position_label}）",
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


def _fmt_bool_mark(value: bool | None) -> str:
    if value is None:
        return "N/A"
    return "〇" if value else "×"


def _fmt_timestamp(value: object) -> str:
    text = str(value).replace(":", "：")
    if " " in text:
        date, time = text.split(" ", 1)
        return f"{date}　{time}分"
    return text


def _format_breakline_pair(
    label: str,
    high: float | None,
    high_distance: float | None,
    high_distance_pct: float | None,
    low: float | None,
    low_distance: float | None,
    low_distance_pct: float | None,
) -> str:
    return (
        f"{label}高値：{_fmt_price(high)}（距離 {_fmt_price_signed(high_distance)} / {_fmt_pct(high_distance_pct)}）　"
        f"{label}安値：{_fmt_price(low)}（距離 {_fmt_price_signed(low_distance)} / {_fmt_pct(low_distance_pct)}）"
    )


def _is_previous_vwap_maintained(result: TechnicalAnalysisResult) -> bool | None:
    prev_close = result.snapshot.price.prev_close
    vwap = _as_float(result.vwap_snapshot.get("vwap"))
    if prev_close is None or vwap is None:
        return None
    return prev_close >= vwap


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


def _trend_symbol(trend: str) -> str:
    if trend == "上昇トレンド":
        return "↑"
    if trend == "下落トレンド":
        return "↓"
    return "→"


def _short_trend_label(trend: str) -> str:
    if trend == "上昇トレンド":
        return "上昇"
    if trend == "下落トレンド":
        return "下落"
    if trend == "N/A":
        return "N/A"
    return "もみあい"


__all__ = ["build_technical_output"]

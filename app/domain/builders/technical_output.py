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
        f"ローソク：{snapshot.previous_session.candle} / {snapshot.previous_session.wick_shape}",
        f"押し判定：{snapshot.previous_session.pullback}",
        "",
        "■節目・ブレイクライン",
        f"5日高値：{_fmt_price(snapshot.breakline.recent5_high)}（距離 {_fmt_price_signed(snapshot.breakline.recent5_high_distance)} / {_fmt_pct(snapshot.breakline.recent5_high_distance_pct)}）",
        f"20日高値：{_fmt_price(snapshot.breakline.recent20_high)}（距離 {_fmt_price_signed(snapshot.breakline.recent20_high_distance)} / {_fmt_pct(snapshot.breakline.recent20_high_distance_pct)}）",
        f"60日高値：{_fmt_price(snapshot.breakline.recent60_high)}（距離 {_fmt_price_signed(snapshot.breakline.recent60_high_distance)} / {_fmt_pct(snapshot.breakline.recent60_high_distance_pct)}）",
        f"60日レンジ位置：{_fmt_position_pct(snapshot.breakline.recent60_range_position)}（{snapshot.breakline.recent60_range_position_label}）",
        "",
        "■流れ",
        snapshot.trend,
    ]
    return "\n".join(lines) + "\n"


def _format_opening_summary(result: TechnicalAnalysisResult) -> str:
    snapshot = result.snapshot
    vwap_snapshot = result.vwap_snapshot
    latest = snapshot.price.latest
    vwap = _as_float(vwap_snapshot.get("vwap"))
    vwap_diff = latest - vwap if latest is not None and vwap is not None else None
    vwap_diff_pct = ((latest / vwap) - 1) * 100 if latest is not None and vwap not in (None, 0) else None
    vwap_source_suffix = " (日足参考値)" if vwap_snapshot.get("vwap_source") == "日足参考値" else ""
    timestamp = vwap_snapshot.get("latest_price_timestamp") or "N/A"
    return "\n".join(
        [
            str(timestamp).replace(":", "："),
            f"株価：{_fmt_price_current(latest)}円（前日比{_fmt_price_signed(snapshot.price.day_change_price)}円：{_fmt_pct(snapshot.price.day_change_pct)}）（{snapshot.range.day_close_position_label} {_fmt_position_pct(snapshot.range.day_close_position)}で終了）",
            f"トレンド：{_trend_symbol(snapshot.trend)}　{_short_trend_label(snapshot.trend)}",
            f"Vwap：{_fmt_price_signed(vwap_diff)}円（{_fmt_pct(vwap_diff_pct)}）{vwap_source_suffix}",
            f"位置：25日線 {_fmt_pct(snapshot.moving_average.dev25_pct)}（ATR比 {_fmt_multiple(snapshot.moving_average.ma25_distance_atr)}）　60日レンジ位置 {_fmt_position_pct(snapshot.breakline.recent60_range_position)}（{snapshot.breakline.recent60_range_position_label}）",
            f"RSI：{_fmt_number(snapshot.rsi14)}",
        ]
    )


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


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


def _fmt_volume(value: float | None) -> str:
    return "N/A" if value is None else f"{value:,.0f}株"


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

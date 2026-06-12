"""Domain policy: technical summary ranks and nearby price lines."""

from __future__ import annotations

from app.domain.models.technical_summary import (
    TechnicalHeadlineSummary,
    TechnicalSummaryLine,
    TechnicalSummaryRank,
)

RANK_LABELS: dict[TechnicalSummaryRank, str] = {
    "A1": "位置良好",
    "A2": "やや過熱",
    "B1": "上昇後半",
    "B2": "過熱極大",
    "C1": "押し目候補",
    "C2": "崩れ警戒",
    "D1": "戻り途中",
    "D2": "底打ち候補",
    "D3": "底打ち初動",
    "E": "下落トレンド",
}

RANK_ORDER: tuple[TechnicalSummaryRank, ...] = ("A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2", "D3", "E")

HEADLINE_COMMENTS: dict[TechnicalSummaryRank, str] = {
    "A1": "順張り可。過熱なし。",
    "A2": "上昇継続中。ただし追いかけ注意。",
    "B1": "値幅は残るが、押しを待つ位置。",
    "B2": "新規買い非推奨。利確優先。",
    "C1": "支持線反発待ち。",
    "C2": "25日線割れ警戒。買いは待ち。",
    "D1": "25日線回復待ち。",
    "D2": "支持線確認中。買いは待ち。",
    "D3": "反転初動。25日線突破確認。",
    "E": "買い見送り。反転確認待ち。",
}

NEXT_ACTIONS: dict[TechnicalSummaryRank, str] = {
    "A1": "深押し、VWAP回復、後場VWAP維持は可。追加買いは条件付き可。",
    "A2": "支持線待ち。追加買いは小さく。",
    "B1": "新規は慎重。追加買い非推奨。",
    "B2": "短期監視のみ。追加買い不可。",
    "C1": "VWAP回復まで買い待ち。",
    "C2": "VWAP回復後も15分維持を確認。追加買い不可。",
    "D1": "後場VWAP維持なら監視継続。追加買いは25日線回復後。",
    "D2": "後場VWAP回復を待つ。追加買い不可。",
    "D3": "深押し、VWAP回復は可。追加買いは25日線回復後。",
    "E": "監視のみ。新規買い不可。",
}

FOCUS_THEME_KEYWORDS = ("半導体", "電線", "AI", "ＡＩ")


def is_focus_theme(name: str) -> bool:
    normalized = name.upper()
    return any(keyword.upper() in normalized for keyword in FOCUS_THEME_KEYWORDS)


def classify_technical_summary_rank(
    *,
    dev25_pct: float,
    latest: float,
    vwap: float,
    focus_theme: bool,
    ma25_distance_atr: float | None = None,
    ma25: float | None = None,
    ma25_prev5: float | None = None,
    rsi14: float | None = None,
    three_session_change_pct: float | None = None,
    high_breakout_count: int | None = None,
    low_higher_count: int | None = None,
    day_close_position: float | None = None,
    volume_vs_avg20_pct: float | None = None,
    recent60_range_position: float | None = None,
) -> TechnicalSummaryRank:
    del focus_theme
    vwap_up = latest >= vwap
    ma25_slope = _ma25_slope(ma25, ma25_prev5)
    range_position_pct = _position_pct(recent60_range_position)
    close_position_pct = _position_pct(day_close_position)

    if dev25_pct >= 10 or _gte(ma25_distance_atr, 2.0):
        if _gte(rsi14, 70) or _gte(three_session_change_pct, 10) or _gte(volume_vs_avg20_pct, 150):
            return "B2"
        return "B2"

    if dev25_pct >= 0:
        if dev25_pct >= 7 and (_gte(three_session_change_pct, 6) or _gte(range_position_pct, 80) or vwap_up):
            return "B1"
        if vwap_up and dev25_pct >= 4:
            return "A2"
        if vwap_up:
            return "A1"
        if dev25_pct <= 3 and (ma25_slope in {"flat", "down"} or low_higher_count == 0):
            return "C2"
        return "C1"

    if vwap_up:
        if (
            _gte(low_higher_count, 2)
            and _gte(high_breakout_count, 1)
            and _gte(close_position_pct, 60)
            and dev25_pct >= -8
        ):
            return "D3"
        return "D1"

    if dev25_pct >= -12 and _gte(close_position_pct, 40):
        return "D2"
    return "E"


def build_technical_headline_summary(
    *,
    dev25_pct: float,
    latest: float,
    vwap: float,
    focus_theme: bool = False,
    ma25_distance_atr: float | None = None,
    ma25: float | None = None,
    ma25_prev5: float | None = None,
    rsi14: float | None = None,
    three_session_change_pct: float | None = None,
    high_breakout_count: int | None = None,
    low_higher_count: int | None = None,
    day_close_position: float | None = None,
    volume_vs_avg20_pct: float | None = None,
    recent60_range_position: float | None = None,
) -> TechnicalHeadlineSummary:
    rank = classify_technical_summary_rank(
        dev25_pct=dev25_pct,
        latest=latest,
        vwap=vwap,
        focus_theme=focus_theme,
        ma25_distance_atr=ma25_distance_atr,
        ma25=ma25,
        ma25_prev5=ma25_prev5,
        rsi14=rsi14,
        three_session_change_pct=three_session_change_pct,
        high_breakout_count=high_breakout_count,
        low_higher_count=low_higher_count,
        day_close_position=day_close_position,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        recent60_range_position=recent60_range_position,
    )
    return TechnicalHeadlineSummary(
        rank=rank,
        rank_label=RANK_LABELS[rank],
        comment=HEADLINE_COMMENTS[rank],
        next_action=NEXT_ACTIONS[rank],
    )


def build_nearby_support_lines(
    *,
    latest: float,
    ma25: float | None,
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
) -> tuple[TechnicalSummaryLine, ...]:
    return _dedupe_lines(
        _lines_below(
            latest,
            (
                TechnicalSummaryLine("25ME", ma25) if ma25 is not None else None,
                TechnicalSummaryLine("PrevL", previous_low) if previous_low is not None else None,
                TechnicalSummaryLine("20D-L", recent20_low) if recent20_low is not None else None,
                TechnicalSummaryLine("75ME", ma75) if ma75 is not None else None,
                TechnicalSummaryLine("60D-L", recent60_low) if recent60_low is not None else None,
            ),
        )
    )[:2]


def build_nearby_resistance_lines(
    *,
    latest: float,
    previous_high: float | None,
    recent20_high: float | None,
    recent60_high: float | None,
    ma25: float | None,
) -> tuple[TechnicalSummaryLine, ...]:
    return _dedupe_lines(
        _lines_above(
            latest,
            (
                TechnicalSummaryLine("PrevH", previous_high) if previous_high is not None else None,
                TechnicalSummaryLine("20D-H", recent20_high) if recent20_high is not None else None,
                TechnicalSummaryLine("60D-H", recent60_high) if recent60_high is not None else None,
                TechnicalSummaryLine("25ME", ma25) if ma25 is not None else None,
            ),
        )
    )[:2]


def _lines_below(
    latest: float,
    lines: tuple[TechnicalSummaryLine | None, ...],
) -> tuple[TechnicalSummaryLine, ...]:
    candidates = [line for line in lines if line is not None and line.price < latest]
    return tuple(sorted(candidates, key=lambda line: line.price, reverse=True))


def _lines_above(
    latest: float,
    lines: tuple[TechnicalSummaryLine | None, ...],
) -> tuple[TechnicalSummaryLine, ...]:
    candidates = [line for line in lines if line is not None and line.price > latest]
    return tuple(sorted(candidates, key=lambda line: line.price))


def _dedupe_lines(lines: tuple[TechnicalSummaryLine, ...]) -> tuple[TechnicalSummaryLine, ...]:
    seen: set[float] = set()
    result: list[TechnicalSummaryLine] = []
    for line in lines:
        if line.price in seen:
            continue
        seen.add(line.price)
        result.append(line)
    return tuple(result)


def _ma25_slope(ma25: float | None, ma25_prev5: float | None) -> str:
    if ma25 is None or ma25_prev5 is None:
        return "unknown"
    if ma25 > ma25_prev5:
        return "up"
    if ma25 < ma25_prev5:
        return "down"
    return "flat"


def _position_pct(value: float | None) -> float | None:
    return None if value is None else value * 100


def _gte(value: float | int | None, threshold: float | int) -> bool:
    return value is not None and value >= threshold


__all__ = [
    "RANK_LABELS",
    "RANK_ORDER",
    "build_technical_headline_summary",
    "build_nearby_resistance_lines",
    "build_nearby_support_lines",
    "classify_technical_summary_rank",
    "is_focus_theme",
]

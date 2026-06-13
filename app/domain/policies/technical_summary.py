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
    "D2": "買い急がず。補助指標の確認待ち。",
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
    day_open: float | None = None,
    day_high: float | None = None,
    day_low: float | None = None,
    atr14: float | None = None,
    volume_vs_avg20_pct: float | None = None,
    recent60_range_position: float | None = None,
    previous_low: float | None = None,
    recent20_low: float | None = None,
    ma75: float | None = None,
    recent60_low: float | None = None,
) -> TechnicalSummaryRank:
    del focus_theme
    vwap_up = latest > vwap
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

    d2_evaluation = _evaluate_d2_bottoming_candidate(
        latest=latest,
        vwap=vwap,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        day_close_position=day_close_position,
        atr14=atr14,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        rsi14=rsi14,
        low_higher_count=low_higher_count,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
    )
    if d2_evaluation == "exclude":
        return "E"
    if dev25_pct >= -12 and d2_evaluation in {"strong", "weak"}:
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
    day_open: float | None = None,
    day_high: float | None = None,
    day_low: float | None = None,
    atr14: float | None = None,
    volume_vs_avg20_pct: float | None = None,
    recent60_range_position: float | None = None,
    previous_low: float | None = None,
    recent20_low: float | None = None,
    ma75: float | None = None,
    recent60_low: float | None = None,
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
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        atr14=atr14,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        recent60_range_position=recent60_range_position,
        previous_low=previous_low,
        recent20_low=recent20_low,
        ma75=ma75,
        recent60_low=recent60_low,
    )
    comment = HEADLINE_COMMENTS[rank]
    next_action = NEXT_ACTIONS[rank]
    if rank == "D2":
        d2_evaluation = _evaluate_d2_bottoming_candidate(
            latest=latest,
            vwap=vwap,
            day_open=day_open,
            day_high=day_high,
            day_low=day_low,
            day_close_position=day_close_position,
            atr14=atr14,
            volume_vs_avg20_pct=volume_vs_avg20_pct,
            rsi14=rsi14,
            low_higher_count=low_higher_count,
            previous_low=previous_low,
            recent20_low=recent20_low,
            ma75=ma75,
            recent60_low=recent60_low,
        )
        if d2_evaluation == "strong":
            comment = "底打ち候補強。"
            next_action = "VWAP回復待ち(補助指標2つ以上)。"
        else:
            comment = "底打ち候補。"
            next_action = "買い急がず(補助指標1つ以下)。"
    return TechnicalHeadlineSummary(
        rank=rank,
        rank_label=RANK_LABELS[rank],
        comment=comment,
        next_action=next_action,
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


def _evaluate_d2_bottoming_candidate(
    *,
    latest: float,
    vwap: float,
    day_open: float | None,
    day_high: float | None,
    day_low: float | None,
    day_close_position: float | None,
    atr14: float | None,
    volume_vs_avg20_pct: float | None,
    rsi14: float | None,
    low_higher_count: int | None,
    previous_low: float | None,
    recent20_low: float | None,
    ma75: float | None,
    recent60_low: float | None,
) -> str:
    if atr14 in (None, 0) or day_low is None or day_high is None or day_open is None:
        return "none"
    support = _nearest_d2_support(
        day_low=day_low,
        atr14=atr14,
        supports=(previous_low, recent20_low, ma75, recent60_low),
    )
    if support is None:
        return "none"
    close_position_pct = _position_pct(day_close_position)
    if not _gte(close_position_pct, 40):
        return "none"
    if latest <= support:
        return "none"
    if latest < vwap - atr14 or latest > vwap:
        return "exclude" if latest < vwap - atr14 else "none"
    if _is_volume_surge_big_bearish(
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        latest=latest,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
    ):
        return "exclude"
    if low_higher_count == 0 and close_position_pct <= 50:
        return "exclude"

    score = _d2_auxiliary_score(
        latest=latest,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        support=support,
        volume_vs_avg20_pct=volume_vs_avg20_pct,
        rsi14=rsi14,
    )
    return "strong" if score >= 2 else "weak"


def _nearest_d2_support(
    *,
    day_low: float,
    atr14: float,
    supports: tuple[float | None, ...],
) -> float | None:
    candidates = [
        support
        for support in supports
        if support is not None and abs(day_low - support) <= 0.35 * atr14
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda support: abs(day_low - support))


def _d2_auxiliary_score(
    *,
    latest: float,
    day_open: float,
    day_high: float,
    day_low: float,
    support: float,
    volume_vs_avg20_pct: float | None,
    rsi14: float | None,
) -> int:
    score = 0
    if _gte(volume_vs_avg20_pct, 80):
        score += 1
    if _lower_wick_ratio(day_open=day_open, day_high=day_high, day_low=day_low, latest=latest) > 0.2:
        score += 1
    if rsi14 is not None and 30 <= rsi14 <= 45:
        score += 1
    if day_low < support:
        score -= 1
    return score


def _is_volume_surge_big_bearish(
    *,
    day_open: float,
    day_high: float,
    day_low: float,
    latest: float,
    volume_vs_avg20_pct: float | None,
) -> bool:
    day_range = day_high - day_low
    if day_range <= 0:
        return False
    body_ratio = abs(latest - day_open) / day_range
    return _gte(volume_vs_avg20_pct, 180) and latest < day_open and body_ratio >= 0.65


def _lower_wick_ratio(*, day_open: float, day_high: float, day_low: float, latest: float) -> float:
    day_range = day_high - day_low
    if day_range <= 0:
        return 0.0
    return max(0.0, min(day_open, latest) - day_low) / day_range


__all__ = [
    "RANK_LABELS",
    "RANK_ORDER",
    "build_technical_headline_summary",
    "build_nearby_resistance_lines",
    "build_nearby_support_lines",
    "classify_technical_summary_rank",
    "is_focus_theme",
]

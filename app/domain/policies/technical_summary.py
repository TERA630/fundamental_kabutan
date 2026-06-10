"""Domain policy: technical summary ranks and nearby price lines."""

from __future__ import annotations

from app.domain.models.technical_summary import TechnicalSummaryLine, TechnicalSummaryRank

RANK_LABELS: dict[TechnicalSummaryRank, str] = {
    "A1": "位置良好",
    "A2": "やや過熱",
    "B1": "過熱後半",
    "B2": "過熱極大",
    "C1": "押し目候補",
    "C2": "回復途上",
    "E": "トレンド弱い",
}

RANK_ORDER: tuple[TechnicalSummaryRank, ...] = ("A1", "A2", "B1", "B2", "C1", "C2", "E")

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
) -> TechnicalSummaryRank:
    vwap_up = latest >= vwap

    if focus_theme:
        if vwap_up and 0 <= dev25_pct < 4:
            return "A1"
        if vwap_up and 4 <= dev25_pct < 7:
            return "A2"
        if 7 <= dev25_pct < 10:
            return "B1"
        if dev25_pct >= 10:
            return "B2"
    else:
        if vwap_up and 0 <= dev25_pct < 5:
            return "A1"
        if vwap_up and 5 <= dev25_pct < 8:
            return "A2"
        if 8 <= dev25_pct < 12:
            return "B1"
        if dev25_pct >= 12:
            return "B2"

    if dev25_pct >= 0 and not vwap_up:
        return "C1"
    if dev25_pct < 0 and vwap_up:
        return "C2"
    return "E"


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


__all__ = [
    "RANK_LABELS",
    "RANK_ORDER",
    "build_nearby_resistance_lines",
    "build_nearby_support_lines",
    "classify_technical_summary_rank",
    "is_focus_theme",
]

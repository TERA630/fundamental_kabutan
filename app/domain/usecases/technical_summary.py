"""Domain use-case: build technical summary rows for a watchlist."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from app.domain.models.technical_summary import (
    SkippedTechnicalSummaryStock,
    TechnicalSummaryRow,
    TechnicalSummaryTable,
)
from app.domain.models.us_market_summary import UsMarketSummaryTable
from app.domain.policies.technical_summary import (
    build_nearby_resistance_lines,
    build_nearby_support_lines,
    build_technical_headline_summary,
    is_focus_theme,
)
from app.domain.usecases.technical_analysis import TechnicalAnalysisResult

BuildTechnicalAnalysisResult = Callable[[str, str], TechnicalAnalysisResult]
BuildUsMarketSummary = Callable[[], UsMarketSummaryTable]


class TechnicalSummaryService:
    """Builds technical summary rows from watchlist entries."""

    def __init__(
        self,
        build_analysis_result: BuildTechnicalAnalysisResult,
        build_us_market_summary: BuildUsMarketSummary | None = None,
    ):
        self.build_analysis_result = build_analysis_result
        self.build_us_market_summary = build_us_market_summary

    def build_summary_table(self, watchlist_entries: Iterable[tuple[str, str]]) -> TechnicalSummaryTable:
        rows: list[TechnicalSummaryRow] = []
        skipped: list[SkippedTechnicalSummaryStock] = []
        for name, code4 in watchlist_entries:
            try:
                result = self.build_analysis_result(name, code4)
                rows.append(self.build_summary_row(result))
            except Exception as exc:
                skipped.append(SkippedTechnicalSummaryStock(name=name, code4=code4, reason=str(exc)))
        us_market = self.build_us_market_summary() if self.build_us_market_summary is not None else None
        return TechnicalSummaryTable(rows=tuple(rows), skipped=tuple(skipped), us_market=us_market)

    def build_summary_row(self, result: TechnicalAnalysisResult) -> TechnicalSummaryRow:
        snapshot = result.snapshot
        price = snapshot.price
        moving_average = snapshot.moving_average
        previous = snapshot.previous_session
        breakline = snapshot.breakline
        latest = _evaluation_price(result)
        dev25_pct = _pct_change(latest, moving_average.ma25)
        vwap = _as_float(result.vwap_snapshot.get("vwap"))
        if latest is None:
            raise ValueError("現在値が取得できません")
        if dev25_pct is None:
            raise ValueError("25日線乖離率が取得できません")
        if vwap is None:
            raise ValueError("VWAPが取得できません")

        evaluation_volume = _evaluation_intraday_field(result, "volume", price.volume)
        evaluation_open = _evaluation_intraday_field(result, "open", getattr(price, "open", None))
        evaluation_high = _evaluation_intraday_field(result, "high", price.high)
        evaluation_low = _evaluation_intraday_field(result, "low", price.low)
        volume_vs_avg20_pct = (
            None
            if evaluation_volume is None or price.volume_avg20 in (None, 0)
            else (evaluation_volume / price.volume_avg20) * 100
        )
        momentum_sessions = getattr(result.three_session_momentum, "sessions", ())
        high_breakout_count = _count_true(session.high_breakout for session in momentum_sessions)
        low_higher_count = _count_true(session.low_higher for session in momentum_sessions)
        day_close_position = _range_position(latest, evaluation_low, evaluation_high)
        ma25_distance_atr = _safe_div(
            None if moving_average.ma25 is None else latest - moving_average.ma25,
            getattr(snapshot.range, "atr14", None),
        )
        headline = build_technical_headline_summary(
            dev25_pct=dev25_pct,
            latest=latest,
            vwap=vwap,
            focus_theme=is_focus_theme(result.name),
            ma25_distance_atr=ma25_distance_atr,
            ma25=moving_average.ma25,
            ma25_prev5=moving_average.ma25_prev5,
            rsi14=getattr(snapshot, "rsi14", None),
            three_session_change_pct=result.three_session_momentum.change_pct,
            high_breakout_count=high_breakout_count,
            low_higher_count=low_higher_count,
            day_close_position=day_close_position,
            day_open=evaluation_open,
            day_high=evaluation_high,
            day_low=evaluation_low,
            atr14=getattr(snapshot.range, "atr14", None),
            volume_vs_avg20_pct=volume_vs_avg20_pct,
            recent60_range_position=breakline.recent60_range_position,
            previous_low=previous.prev_low,
            recent20_low=breakline.recent20_low,
            ma75=moving_average.ma75,
            recent60_low=breakline.recent60_low,
            vwap_maintained_15m=_as_bool(result.vwap_snapshot.get("vwap_maintained_15m")),
            low_highers=tuple(session.low_higher for session in momentum_sessions),
        )
        return TechnicalSummaryRow(
            name=result.name,
            code4=result.code4,
            rank=headline.rank,
            rank_label=headline.rank_label,
            latest=latest,
            day_change_price=(
                latest - price.prev_close
                if getattr(price, "prev_close", None) is not None
                else price.day_change_price
            ),
            day_change_pct=(
                _pct_change(latest, price.prev_close)
                if getattr(price, "prev_close", None) is not None
                else price.day_change_pct
            ),
            three_session_change_pct=result.three_session_momentum.change_pct,
            day_high=evaluation_high,
            day_low=evaluation_low,
            day_close_position=day_close_position,
            day_range_atr=_safe_div(
                None
                if evaluation_high is None or evaluation_low is None
                else evaluation_high - evaluation_low,
                getattr(snapshot.range, "atr14", None),
            ),
            vwap=vwap,
            vwap_diff_pct=_pct_change(latest, vwap),
            dev25_pct=dev25_pct,
            ma25_distance_atr=ma25_distance_atr,
            volume_vs_avg20_pct=volume_vs_avg20_pct,
            previous_vwap_maintained=_previous_vwap_maintained(result),
            support_lines=build_nearby_support_lines(
                latest=latest,
                ma25=moving_average.ma25,
                previous_low=previous.prev_low,
                recent20_low=breakline.recent20_low,
                ma75=moving_average.ma75,
                recent60_low=breakline.recent60_low,
            ),
            resistance_lines=build_nearby_resistance_lines(
                latest=latest,
                previous_high=previous.prev_high,
                recent20_high=breakline.recent20_high,
                recent60_high=breakline.recent60_high,
                ma25=moving_average.ma25,
            ),
            recent60_range_position=breakline.recent60_range_position,
            headline_comment=headline.comment,
            next_action=headline.next_action,
        )


def _previous_vwap_maintained(result: TechnicalAnalysisResult) -> bool | None:
    previous = result.previous_intraday_snapshot
    am = previous.get("prev_am_vwap_maintained")
    pm = previous.get("prev_pm_vwap_maintained")
    if isinstance(am, bool) and isinstance(pm, bool):
        return am and pm
    return None


def _pct_change(current: float | None, reference: float | None) -> float | None:
    if current is None or reference in (None, 0):
        return None
    return ((current / reference) - 1) * 100


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _evaluation_price(result: TechnicalAnalysisResult) -> float | None:
    value = getattr(result, "evaluation_price", None)
    return _as_float(value) if value is not None else result.snapshot.price.latest


def _evaluation_intraday_field(
    result: TechnicalAnalysisResult,
    key: str,
    daily_value: float | None,
) -> float | None:
    source = getattr(result, "evaluation_price_source", "daily_close")
    if source in {"intraday_5m", "provisional_close"}:
        value = _as_float(result.vwap_snapshot.get(key))
        if value is not None:
            return value
    return daily_value


def _range_position(latest: float, low: float | None, high: float | None) -> float | None:
    if low is None or high is None or high <= low:
        return None
    return (latest - low) / (high - low)


def _safe_div(value: float | None, divisor: float | None) -> float | None:
    if value is None or divisor in (None, 0):
        return None
    return value / divisor


def _count_true(values: Iterable[bool | None]) -> int:
    return sum(1 for value in values if value is True)


__all__ = ["TechnicalSummaryService"]

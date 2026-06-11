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
    RANK_LABELS,
    build_nearby_resistance_lines,
    build_nearby_support_lines,
    classify_technical_summary_rank,
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
        latest = price.latest
        dev25_pct = moving_average.dev25_pct
        vwap = _as_float(result.vwap_snapshot.get("vwap"))
        if latest is None:
            raise ValueError("現在値が取得できません")
        if dev25_pct is None:
            raise ValueError("25日線乖離率が取得できません")
        if vwap is None:
            raise ValueError("VWAPが取得できません")

        rank = classify_technical_summary_rank(
            dev25_pct=dev25_pct,
            latest=latest,
            vwap=vwap,
            focus_theme=is_focus_theme(result.name),
        )
        return TechnicalSummaryRow(
            name=result.name,
            code4=result.code4,
            rank=rank,
            rank_label=RANK_LABELS[rank],
            latest=latest,
            day_change_price=price.day_change_price,
            day_change_pct=price.day_change_pct,
            three_session_change_pct=result.three_session_momentum.change_pct,
            day_high=price.high,
            day_low=price.low,
            day_close_position=getattr(snapshot.range, "day_close_position", None),
            day_range_atr=snapshot.range.day_range_atr,
            vwap=vwap,
            vwap_diff_pct=_pct_change(latest, vwap),
            dev25_pct=dev25_pct,
            ma25_distance_atr=moving_average.ma25_distance_atr,
            volume_vs_avg20_pct=None
            if price.volume is None or price.volume_avg20 in (None, 0)
            else (price.volume / price.volume_avg20) * 100,
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


__all__ = ["TechnicalSummaryService"]

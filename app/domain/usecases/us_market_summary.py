"""Domain use-case: build US market technical summary rows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pandas as pd

from app.domain.models.us_market_summary import (
    SkippedUsMarketSummaryItem,
    UsMarketSummaryRow,
    UsMarketSummaryTable,
)
from app.domain.policies.technical_indicators import calc_rsi14, normalize_daily_history

FetchDailyHistory = Callable[[str], pd.DataFrame]

US_MARKET_ITEMS: tuple[tuple[str, str], ...] = (
    ("NASDAQ総合", "^IXIC"),
    ("SOX指数", "^SOX"),
    ("NVIDIA", "NVDA"),
    ("GRID", "GRID"),
    ("日経先物", "NKD=F"),
    ("銅先物(COMEX)", "HG=F"),
    ("WTI原油", "CL=F"),
)


class UsMarketSummaryService:
    """Builds US market indicator rows from daily histories."""

    def __init__(
        self,
        fetch_daily_history: FetchDailyHistory,
        *,
        clock: Callable[[], datetime] = datetime.now,
    ):
        self.fetch_daily_history = fetch_daily_history
        self.clock = clock

    def build_summary_table(self) -> UsMarketSummaryTable:
        rows: list[UsMarketSummaryRow] = []
        skipped: list[SkippedUsMarketSummaryItem] = []
        for name, ticker in US_MARKET_ITEMS:
            try:
                rows.append(self._build_row(name=name, ticker=ticker))
            except Exception as exc:
                skipped.append(SkippedUsMarketSummaryItem(name=name, ticker=ticker, reason=str(exc)))
        return UsMarketSummaryTable(as_of=self.clock(), rows=tuple(rows), skipped=tuple(skipped))

    def _build_row(self, *, name: str, ticker: str) -> UsMarketSummaryRow:
        history = normalize_daily_history(self.fetch_daily_history(ticker))
        if len(history) < 30:
            raise ValueError("日足価格データが不足しています: 30件以上必要です")

        close = history["Close"]
        latest = _none_if_nan(close.iloc[-1])
        previous = _none_if_nan(close.iloc[-2])
        ma5 = _none_if_nan(close.rolling(5).mean().iloc[-1])
        ma25 = _none_if_nan(close.rolling(25).mean().iloc[-1])
        rsi14 = _none_if_nan(calc_rsi14(close).iloc[-1])
        return UsMarketSummaryRow(
            name=name,
            ticker=ticker,
            latest=latest,
            day_change_pct=_pct_change(latest, previous),
            dev5_pct=_pct_change(latest, ma5),
            dev25_pct=_pct_change(latest, ma25),
            rsi14=rsi14,
        )


def _none_if_nan(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _pct_change(current: float | None, reference: float | None) -> float | None:
    if current is None or reference in (None, 0):
        return None
    return ((current / reference) - 1) * 100


__all__ = ["US_MARKET_ITEMS", "UsMarketSummaryService"]

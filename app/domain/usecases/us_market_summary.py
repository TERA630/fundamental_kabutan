"""Domain use-case: build US market summary rows for technical summary."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from app.domain.models.us_market_summary import (
    SkippedUsMarketSummaryItem,
    UsMarketSummaryRow,
    UsMarketSummaryTable,
)
from app.domain.policies.technical_indicators import calc_rsi14

JST = ZoneInfo("Asia/Tokyo")

US_MARKET_TARGETS: tuple[tuple[str, str], ...] = (
    ("NASDAQ総合", "^IXIC"),
    ("SOX指数", "^SOX"),
    ("NVIDIA", "NVDA"),
    ("GRID", "GRID"),
    ("日経先物", "NKD=F"),
    ("銅先物(COMEX)", "HG=F"),
    ("WTI原油", "CL=F"),
)

FetchUsMarketHistory = Callable[[str], pd.DataFrame]


class UsMarketSummaryService:
    def __init__(
        self,
        fetch_history: FetchUsMarketHistory | None = None,
        now: Callable[[], datetime] | None = None,
    ):
        self.fetch_history = fetch_history or _fetch_yfinance_history
        self.now = now or (lambda: datetime.now(JST))

    def build_summary_table(self) -> UsMarketSummaryTable:
        rows: list[UsMarketSummaryRow] = []
        skipped: list[SkippedUsMarketSummaryItem] = []
        for name, ticker in US_MARKET_TARGETS:
            try:
                rows.append(self.build_summary_row(name=name, ticker=ticker))
            except Exception as exc:
                skipped.append(SkippedUsMarketSummaryItem(name=name, ticker=ticker, reason=str(exc)))
        return UsMarketSummaryTable(as_of=self.now(), rows=tuple(rows), skipped=tuple(skipped))

    def build_summary_row(self, *, name: str, ticker: str) -> UsMarketSummaryRow:
        history = self.fetch_history(ticker)
        close = _close_series(history)
        if len(close) < 2:
            raise ValueError("価格履歴が不足しています")

        latest = _as_float(close.iloc[-1])
        previous = _as_float(close.iloc[-2])
        ma5 = _as_float(close.rolling(5).mean().iloc[-1]) if len(close) >= 5 else None
        ma25 = _as_float(close.rolling(25).mean().iloc[-1]) if len(close) >= 25 else None
        rsi14 = _as_float(calc_rsi14(close).iloc[-1]) if len(close) >= 15 else None
        return UsMarketSummaryRow(
            name=name,
            ticker=ticker,
            latest=latest,
            day_change_pct=_pct_change(latest, previous),
            dev5_pct=_pct_change(latest, ma5),
            dev25_pct=_pct_change(latest, ma25),
            rsi14=rsi14,
        )


def _fetch_yfinance_history(ticker: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.Ticker(ticker).history(period="3mo", interval="1d", auto_adjust=False)


def _close_series(history: pd.DataFrame) -> pd.Series:
    if history.empty or "Close" not in history.columns:
        raise ValueError("Close列が取得できません")
    close = pd.to_numeric(history["Close"], errors="coerce").dropna()
    if close.empty:
        raise ValueError("終値が取得できません")
    return close


def _as_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _pct_change(current: float | None, reference: float | None) -> float | None:
    if current is None or reference in (None, 0):
        return None
    return ((current / reference) - 1) * 100


__all__ = ["US_MARKET_TARGETS", "UsMarketSummaryService"]

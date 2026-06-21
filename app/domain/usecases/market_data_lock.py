"""Process-wide synchronization for intraday market-data retrieval."""

from __future__ import annotations

from threading import RLock

import pandas as pd


# A yfinance intraday request and its cache update must be one atomic operation.
# The lock is shared by every MarketDataService instance in this process.
INTRADAY_MARKET_DATA_LOCK = RLock()
INTRADAY_PRICE_DEVIATION_LIMIT = 0.30


def is_intraday_history_consistent(
    intraday_history: pd.DataFrame,
    daily_history: pd.DataFrame | None,
) -> bool:
    """Reject a mixed-symbol five-minute response before caching it."""

    if daily_history is None or intraday_history.empty or daily_history.empty:
        return True
    try:
        intraday_close = float(intraday_history["Close"].dropna().iloc[-1])
        daily_close = float(daily_history["Close"].dropna().iloc[-1])
        intraday_date = pd.Timestamp(intraday_history.index[-1]).date()
        daily_date = pd.Timestamp(daily_history.index[-1]).date()
    except (IndexError, KeyError, TypeError, ValueError):
        return False
    if intraday_date != daily_date or intraday_close <= 0 or daily_close <= 0:
        return True
    return abs((intraday_close / daily_close) - 1) <= INTRADAY_PRICE_DEVIATION_LIMIT


__all__ = [
    "INTRADAY_MARKET_DATA_LOCK",
    "INTRADAY_PRICE_DEVIATION_LIMIT",
    "is_intraday_history_consistent",
]

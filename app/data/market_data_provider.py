"""Data-layer market data providers (yfinance)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.data.utils import safe_float
from app.domain.models.analyst_estimates import AnalystEstimates, EpsRevisionPeriod
from app.domain.models.market_data import MarketSnapshot
from app.domain.policies.market_history import (
    TECH_DAILY_COLUMNS,
    TECH_DAILY_HISTORY_TTL_SEC,
    TECH_INTRADAY_HISTORY_TTL_SEC,
    build_daily_reference_vwap_snapshot,
    build_intraday_vwap_snapshot,
    build_market_snapshot_from_daily_history,
    build_previous_session_intraday_snapshot,
    build_technical_daily_history_cache_key,
    build_technical_intraday_history_cache_key,
    empty_history,
    normalize_history_frame,
)

try:
    import yfinance as yf
except ImportError:
    yf = None


def fetch_yfinance_market_snapshot(code4: str, *, daily_history: pd.DataFrame | None = None) -> MarketSnapshot:
    result = build_market_snapshot_from_daily_history(daily_history).to_dict() if daily_history is not None else MarketSnapshot.empty().to_dict()
    if yf is None:
        return MarketSnapshot.from_mapping(result)
    try:
        ticker = yf.Ticker(f"{code4}.T")
        if daily_history is None:
            hist = ticker.history(period="5d", auto_adjust=False)
            result.update(build_market_snapshot_from_daily_history(hist).to_dict())
        try:
            info = getattr(ticker, "fast_info", None)
            if info is not None:
                result["market_cap"] = safe_float(getattr(info, "market_cap", None) or info.get("market_cap"))
        except Exception:
            pass
        try:
            info2 = getattr(ticker, "info", None) or {}
            result["per"] = safe_float(info2.get("trailingPE") or info2.get("forwardPE"))
            result["pbr"] = safe_float(info2.get("priceToBook"))
            result["industry"] = info2.get("sector") or info2.get("industry")
            dy = safe_float(info2.get("dividendYield"))
            result["div_yield"] = None if dy is None else (dy * 100 if dy <= 1 else dy)
            po = safe_float(info2.get("payoutRatio"))
            result["payout_ratio"] = None if po is None else (po * 100 if po <= 1 else po)
        except Exception:
            pass
    except Exception:
        return MarketSnapshot.from_mapping(result)
    return MarketSnapshot.from_mapping(result)


def fetch_yfinance_snapshot(code4: str, *, daily_history: pd.DataFrame | None = None) -> dict[str, float | str | None]:
    return fetch_yfinance_market_snapshot(code4, daily_history=daily_history).to_dict()


def fetch_yfinance_analyst_estimates(code4: str) -> AnalystEstimates:
    if yf is None:
        return AnalystEstimates.empty()
    try:
        ticker = yf.Ticker(f"{code4}.T")
        info = getattr(ticker, "info", None) or {}
        eps_revisions = _get_eps_revisions_frame(ticker)
        return AnalystEstimates(
            target_mean_price=safe_float(info.get("targetMeanPrice")),
            number_of_analyst_opinions=_safe_int(info.get("numberOfAnalystOpinions")),
            current_year_eps_revisions=_build_eps_revision_period(eps_revisions, "0y"),
            next_year_eps_revisions=_build_eps_revision_period(eps_revisions, "+1y"),
        )
    except Exception:
        return AnalystEstimates.empty()


def _safe_int(value: Any) -> int | None:
    number = safe_float(value)
    if number is None:
        return None
    return int(number)


def _get_eps_revisions_frame(ticker: Any) -> Any:
    if hasattr(ticker, "eps_revisions"):
        return getattr(ticker, "eps_revisions", None)
    return getattr(ticker, "eps_revisons", None)


def _pick_frame_row(frame_like: Any, row_key: str) -> pd.Series | None:
    if frame_like is None:
        return None
    frame = pd.DataFrame(frame_like)
    if frame.empty:
        return None
    candidates = (row_key, row_key.replace("+1y", "+1"), row_key.replace("+", ""))
    for key in candidates:
        if key in frame.index:
            return frame.loc[key]
    return None


def _frame_value(frame_like: Any, row_key: str, column: str) -> Any:
    row = _pick_frame_row(frame_like, row_key)
    if row is None or column not in row:
        return None
    return row[column]


def _build_eps_revision_period(frame_like: Any, row_key: str) -> EpsRevisionPeriod:
    return EpsRevisionPeriod(
        up_last_30_days=_safe_int(_frame_value(frame_like, row_key, "upLast30days")),
        down_last_30_days=_safe_int(_frame_value(frame_like, row_key, "downLast30days")),
    )


def fetch_yfinance_daily_history(code4: str, *, period: str = "4mo", interval: str = "1d") -> pd.DataFrame:
    if yf is None:
        return empty_history()
    try:
        ticker = yf.Ticker(f"{code4}.T")
        history = ticker.history(period=period, interval=interval, auto_adjust=False)
        return normalize_history_frame(history)
    except Exception:
        return empty_history()


def fetch_yfinance_symbol_daily_history(symbol: str, *, period: str = "4mo", interval: str = "1d") -> pd.DataFrame:
    if yf is None:
        return empty_history()
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval=interval, auto_adjust=False)
        return normalize_history_frame(history)
    except Exception:
        return empty_history()


def fetch_yfinance_intraday_history(code4: str, *, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
    if yf is None:
        return empty_history()
    try:
        history = yf.download(f"{code4}.T", period=period, interval=interval, auto_adjust=False, progress=False)
        return normalize_history_frame(history)
    except Exception:
        return empty_history()


def fetch_yfinance_vwap_snapshot(code4: str, *, daily_history: pd.DataFrame | None = None, interval: str = "5m") -> dict[str, float | str | None]:
    intraday = fetch_yfinance_intraday_history(code4, interval=interval)
    if not intraday.empty:
        return build_intraday_vwap_snapshot(intraday)

    daily = daily_history if daily_history is not None else fetch_yfinance_daily_history(code4)
    return build_daily_reference_vwap_snapshot(daily)


__all__ = [
    "TECH_DAILY_COLUMNS",
    "TECH_DAILY_HISTORY_TTL_SEC",
    "TECH_INTRADAY_HISTORY_TTL_SEC",
    "build_daily_reference_vwap_snapshot",
    "build_market_snapshot_from_daily_history",
    "build_intraday_vwap_snapshot",
    "build_previous_session_intraday_snapshot",
    "build_technical_daily_history_cache_key",
    "build_technical_intraday_history_cache_key",
    "fetch_yfinance_daily_history",
    "fetch_yfinance_symbol_daily_history",
    "fetch_yfinance_intraday_history",
    "fetch_yfinance_analyst_estimates",
    "fetch_yfinance_market_snapshot",
    "fetch_yfinance_snapshot",
    "fetch_yfinance_vwap_snapshot",
]

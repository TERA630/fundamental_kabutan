"""Data-layer market data providers (yfinance)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.data.utils import safe_float
from app.domain.models.analyst_estimates import AnalystEstimates, EpsRevisionPeriod
from app.domain.models.market_data import MarketSnapshot

try:
    import yfinance as yf
except ImportError:
    yf = None

TECH_DAILY_HISTORY_TTL_SEC = 12 * 60 * 60
TECH_INTRADAY_HISTORY_TTL_SEC = 5 * 60
TECH_DAILY_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


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


def build_technical_daily_history_cache_key(code4: str, *, period: str = "4mo", interval: str = "1d") -> str:
    return f"tech_daily_{code4}_{period}_{interval}"


def build_technical_intraday_history_cache_key(code4: str, *, interval: str = "5m") -> str:
    return f"tech_intraday_{code4}_{interval}_jst"


def _empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=list(TECH_DAILY_COLUMNS))


def _normalize_history_frame(history: Any) -> pd.DataFrame:
    if history is None:
        return _empty_history()
    frame = pd.DataFrame(history).copy()
    if frame.empty:
        return _empty_history()

    if isinstance(frame.columns, pd.MultiIndex):
        if len(frame.columns.names) >= 2:
            level_values = set(frame.columns.get_level_values(0))
            if set(TECH_DAILY_COLUMNS).issubset(level_values):
                frame.columns = frame.columns.get_level_values(0)
            else:
                frame.columns = frame.columns.get_level_values(-1)
        else:
            frame.columns = frame.columns.get_level_values(0)

    missing = [column for column in TECH_DAILY_COLUMNS if column not in frame.columns]
    if missing:
        return _empty_history()

    out = frame.loc[:, list(TECH_DAILY_COLUMNS)].copy()
    for column in TECH_DAILY_COLUMNS:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    if hasattr(out.index, "tz") and out.index.tz is not None:
        out.index = out.index.tz_convert("Asia/Tokyo").tz_localize(None)
    return out


def build_market_snapshot_from_daily_history(daily_history: pd.DataFrame | None) -> MarketSnapshot:
    daily = _normalize_history_frame(daily_history)
    if daily.empty:
        return MarketSnapshot.empty()

    close = daily["Close"].dropna()
    if close.empty:
        return MarketSnapshot.empty()

    return MarketSnapshot(
        price=safe_float(close.iloc[-1]),
        as_of=_latest_timestamp_label(daily.index[-1], fallback_suffix="終値"),
    )


def fetch_yfinance_daily_history(code4: str, *, period: str = "4mo", interval: str = "1d") -> pd.DataFrame:
    if yf is None:
        return _empty_history()
    try:
        ticker = yf.Ticker(f"{code4}.T")
        history = ticker.history(period=period, interval=interval, auto_adjust=False)
        return _normalize_history_frame(history)
    except Exception:
        return _empty_history()


def fetch_yfinance_intraday_history(code4: str, *, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
    if yf is None:
        return _empty_history()
    try:
        history = yf.download(f"{code4}.T", period=period, interval=interval, auto_adjust=False, progress=False)
        return _normalize_history_frame(history)
    except Exception:
        return _empty_history()


def _latest_timestamp_label(index_value: Any, *, fallback_suffix: str) -> str | None:
    try:
        timestamp = pd.Timestamp(index_value)
    except Exception:
        return fallback_suffix
    if pd.isna(timestamp):
        return fallback_suffix
    timestamp = timestamp.tz_localize(None) if timestamp.tzinfo is not None else timestamp
    if fallback_suffix == "終値":
        return f"{timestamp.date().isoformat()} 終値"
    return f"{timestamp.date().isoformat()} {timestamp.strftime('%H:%M')}"


def build_daily_reference_vwap_snapshot(daily_history: pd.DataFrame) -> dict[str, float | str | None]:
    daily = _normalize_history_frame(daily_history)
    if daily.empty:
        return {
            "latest": None,
            "open": None,
            "high": None,
            "low": None,
            "volume": None,
            "vwap": None,
            "latest_bar_time": None,
            "latest_price_source": "daily_close",
            "latest_price_timestamp": None,
            "vwap_source": "日足参考値",
            "vwap_timestamp": None,
        }
    row = daily.iloc[-1]
    vwap = (float(row["High"]) + float(row["Low"]) + float(row["Close"])) / 3
    timestamp = _latest_timestamp_label(daily.index[-1], fallback_suffix="終値")
    return {
        "latest": safe_float(row["Close"]),
        "open": safe_float(row["Open"]),
        "high": safe_float(row["High"]),
        "low": safe_float(row["Low"]),
        "volume": safe_float(row["Volume"]),
        "vwap": vwap,
        "latest_bar_time": "終値",
        "latest_price_source": "daily_close",
        "latest_price_timestamp": timestamp,
        "vwap_source": "日足参考値",
        "vwap_timestamp": timestamp,
    }


def build_intraday_vwap_snapshot(intraday_history: pd.DataFrame) -> dict[str, float | str | None]:
    intraday = _normalize_history_frame(intraday_history)
    intraday = intraday[intraday["Volume"] > 0]
    intraday = _latest_intraday_session(intraday)
    if intraday.empty:
        return build_daily_reference_vwap_snapshot(_empty_history())

    typical_price = (intraday["High"] + intraday["Low"] + intraday["Close"]) / 3
    weighted = (typical_price * intraday["Volume"]).cumsum()
    volume_sum = intraday["Volume"].cumsum()
    vwap_series = weighted / volume_sum
    row = intraday.iloc[-1]
    timestamp = _latest_timestamp_label(intraday.index[-1], fallback_suffix="")
    latest_bar_time = pd.Timestamp(intraday.index[-1]).strftime("%H:%M")
    return {
        "latest": safe_float(row["Close"]),
        "open": safe_float(intraday.iloc[0]["Open"]),
        "high": safe_float(intraday["High"].max()),
        "low": safe_float(intraday["Low"].min()),
        "volume": safe_float(intraday["Volume"].sum()),
        "vwap": safe_float(vwap_series.iloc[-1]),
        "latest_bar_time": latest_bar_time,
        "latest_price_source": "intraday_5m",
        "latest_price_timestamp": timestamp,
        "vwap_source": "本日5分足",
        "vwap_timestamp": timestamp,
    }


def _latest_intraday_session(intraday: pd.DataFrame) -> pd.DataFrame:
    if intraday.empty:
        return intraday
    latest_date = pd.Timestamp(intraday.index[-1]).date()
    dates = pd.Series(intraday.index.date, index=intraday.index)
    return intraday[dates == latest_date]


def _empty_previous_session_intraday_snapshot() -> dict[str, float | str | bool | None]:
    return {
        "prev_vwap": None,
        "prev_vwap_source": None,
        "prev_am_vwap": None,
        "prev_pm_vwap": None,
        "prev_am_vwap_maintained": None,
        "prev_pm_vwap_maintained": None,
        "previous_pm_vwap_position": "N/A",
        "previous_pm_evaluation": "N/A",
        "pm_open": None,
        "pm_high": None,
        "pm_low": None,
        "pm_return_pct": None,
        "pm_close_position": None,
    }


def _calc_vwap(frame: pd.DataFrame) -> float | None:
    if frame.empty:
        return None
    typical_price = (frame["High"] + frame["Low"] + frame["Close"]) / 3
    volume_sum = frame["Volume"].sum()
    if volume_sum == 0:
        return None
    return safe_float((typical_price * frame["Volume"]).sum() / volume_sum)


def _classify_previous_pm_evaluation(
    *,
    pm_open: float | None,
    pm_high: float | None,
    pm_low: float | None,
    close: float | None,
    vwap: float | None,
) -> str:
    if None in (pm_open, pm_high, pm_low, close, vwap) or pm_high <= pm_low:
        return "N/A"
    pm_return_pct = ((close / pm_open) - 1) * 100 if pm_open != 0 else None
    pm_close_position = (close - pm_low) / (pm_high - pm_low)
    if pm_return_pct is None:
        return "N/A"
    if close <= vwap:
        return "後場VWAP割"
    if pm_return_pct < -1 or pm_close_position < 0.30:
        return "失速もVWAP維持"
    if close > pm_open and pm_close_position >= 0.70:
        return "後場上昇"
    if pm_close_position >= 0.50 and -1 <= pm_return_pct <= 1:
        return "高値維持"
    if 0.30 <= pm_close_position < 0.50 and -1 <= pm_return_pct <= 1:
        return "横ばいVWAP維持"
    if pm_return_pct > 1:
        return "後場上昇"
    return "横ばいVWAP維持"


def build_previous_session_intraday_snapshot(
    daily_history: pd.DataFrame,
    intraday_history: pd.DataFrame,
) -> dict[str, float | str | bool | None]:
    daily = _normalize_history_frame(daily_history)
    intraday = _normalize_history_frame(intraday_history)
    intraday = intraday[intraday["Volume"] > 0]
    if len(daily) < 2 or intraday.empty:
        return _empty_previous_session_intraday_snapshot()

    prev_row = daily.iloc[-2]
    prev_date = pd.Timestamp(daily.index[-2]).date()
    prev_close = safe_float(prev_row["Close"])
    session = intraday[pd.Series(intraday.index.date, index=intraday.index) == prev_date]
    if session.empty:
        return _empty_previous_session_intraday_snapshot()

    times = pd.Series(intraday.index.time, index=intraday.index)
    am = session[times.loc[session.index] < pd.Timestamp("12:30").time()]
    pm = session[times.loc[session.index] >= pd.Timestamp("12:30").time()]
    if am.empty or pm.empty:
        return _empty_previous_session_intraday_snapshot()

    prev_vwap = _calc_vwap(session)
    am_vwap = _calc_vwap(am)
    pm_vwap = _calc_vwap(pm)
    am_close = safe_float(am.iloc[-1]["Close"])
    pm_open = safe_float(pm.iloc[0]["Open"])
    pm_high = safe_float(pm["High"].max())
    pm_low = safe_float(pm["Low"].min())
    pm_return_pct = ((prev_close / pm_open) - 1) * 100 if prev_close is not None and pm_open not in (None, 0) else None
    pm_close_position = (prev_close - pm_low) / (pm_high - pm_low) if prev_close is not None and pm_high is not None and pm_low is not None and pm_high > pm_low else None
    return {
        "prev_vwap": prev_vwap,
        "prev_vwap_source": "前日5分足",
        "prev_am_vwap": am_vwap,
        "prev_pm_vwap": pm_vwap,
        "prev_am_vwap_maintained": None if am_close is None or am_vwap is None else am_close >= am_vwap,
        "prev_pm_vwap_maintained": None if prev_close is None or pm_vwap is None else prev_close >= pm_vwap,
        "previous_pm_vwap_position": "N/A" if prev_close is None or pm_vwap is None else ("上" if prev_close > pm_vwap else "下"),
        "previous_pm_evaluation": _classify_previous_pm_evaluation(
            pm_open=pm_open,
            pm_high=pm_high,
            pm_low=pm_low,
            close=prev_close,
            vwap=pm_vwap,
        ),
        "pm_open": pm_open,
        "pm_high": pm_high,
        "pm_low": pm_low,
        "pm_return_pct": pm_return_pct,
        "pm_close_position": pm_close_position,
    }


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
    "fetch_yfinance_intraday_history",
    "fetch_yfinance_analyst_estimates",
    "fetch_yfinance_market_snapshot",
    "fetch_yfinance_snapshot",
    "fetch_yfinance_vwap_snapshot",
]

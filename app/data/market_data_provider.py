"""Data-layer market data providers (yfinance)."""

from __future__ import annotations

from app.data.utils import safe_float

try:
    import yfinance as yf
except ImportError:
    yf = None


def fetch_yfinance_snapshot(code4: str) -> dict[str, float | str | None]:
    result = {"price": None, "market_cap": None, "per": None, "pbr": None, "industry": None, "div_yield": None, "payout_ratio": None}
    if yf is None:
        return result
    try:
        ticker = yf.Ticker(f"{code4}.T")
        hist = ticker.history(period="5d", auto_adjust=False)
        if hist is not None and not hist.empty:
            result["price"] = safe_float(hist["Close"].dropna().iloc[-1])
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
        return result
    return result


__all__ = ["fetch_yfinance_snapshot"]

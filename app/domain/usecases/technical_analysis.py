"""Domain use-case: orchestration for technical analysis output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

import pandas as pd

from app.data.market_data_provider import (
    TECH_DAILY_HISTORY_TTL_SEC,
    TECH_INTRADAY_HISTORY_TTL_SEC,
    build_daily_reference_vwap_snapshot,
    build_intraday_vwap_snapshot,
    build_previous_session_intraday_snapshot,
    build_technical_daily_history_cache_key,
    build_technical_intraday_history_cache_key,
    fetch_yfinance_daily_history,
    fetch_yfinance_intraday_history,
)
from app.domain.models.market_data import MarketDataBundle
from app.domain.models.technical_snapshot import TechnicalSnapshot
from app.domain.policies.technical_indicators import build_technical_snapshot


class TechnicalHistoryCachePort(Protocol):
    def get(self, key: str, ttl_sec: int) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...


TechnicalHistoryProvider = Callable[[str], pd.DataFrame]


@dataclass(frozen=True)
class TechnicalAnalysisResult:
    name: str
    code4: str
    snapshot: TechnicalSnapshot
    intraday_price_timestamp: str | None
    vwap_snapshot: dict[str, float | str | None]
    previous_intraday_snapshot: dict[str, float | str | bool | None]


def dataframe_to_cache_payload(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "index": [str(value) for value in frame.index],
        "columns": list(frame.columns),
        "data": frame.astype(object).where(pd.notna(frame), None).values.tolist(),
    }


def dataframe_from_cache_payload(payload: Any) -> pd.DataFrame | None:
    if not isinstance(payload, dict):
        return None
    index = payload.get("index")
    columns = payload.get("columns")
    data = payload.get("data")
    if not isinstance(index, list) or not isinstance(columns, list) or not isinstance(data, list):
        return None
    try:
        parsed_index = pd.to_datetime(index)
        return pd.DataFrame(data, index=parsed_index, columns=columns)
    except Exception:
        return None


class TechnicalAnalysisService:
    """Builds a technical analysis result from cached or fetched market histories."""

    def __init__(
        self,
        file_cache: TechnicalHistoryCachePort,
        fetch_daily_history: TechnicalHistoryProvider | None = None,
        fetch_intraday_history: TechnicalHistoryProvider | None = None,
    ):
        self.file_cache = file_cache
        self.fetch_daily_history = fetch_daily_history or fetch_yfinance_daily_history
        self.fetch_intraday_history = fetch_intraday_history or fetch_yfinance_intraday_history

    def build_analysis_result(self, *, name: str, code4: str) -> TechnicalAnalysisResult:
        daily_history = self.fetch_daily_history_cached(code4)
        intraday_history = self.fetch_intraday_history_cached(code4)
        return self.build_analysis_result_from_histories(
            name=name,
            code4=code4,
            daily_history=daily_history,
            intraday_history=intraday_history,
        )

    @staticmethod
    def build_analysis_result_from_bundle(*, name: str, bundle: MarketDataBundle) -> TechnicalAnalysisResult:
        return TechnicalAnalysisService.build_analysis_result_from_histories(
            name=name,
            code4=bundle.code4,
            daily_history=bundle.daily_history,
            intraday_history=bundle.intraday_history,
        )

    @staticmethod
    def build_analysis_result_from_histories(
        *,
        name: str,
        code4: str,
        daily_history: pd.DataFrame,
        intraday_history: pd.DataFrame,
    ) -> TechnicalAnalysisResult:
        snapshot = build_technical_snapshot(daily_history)
        vwap_snapshot = (
            build_intraday_vwap_snapshot(intraday_history)
            if not intraday_history.empty
            else build_daily_reference_vwap_snapshot(daily_history)
        )
        previous_intraday_snapshot = build_previous_session_intraday_snapshot(daily_history, intraday_history)
        return TechnicalAnalysisResult(
            name=name,
            code4=code4,
            snapshot=snapshot,
            intraday_price_timestamp=_as_optional_str(vwap_snapshot.get("latest_price_timestamp")),
            vwap_snapshot=vwap_snapshot,
            previous_intraday_snapshot=previous_intraday_snapshot,
        )

    def fetch_daily_history_cached(self, code4: str) -> pd.DataFrame:
        key = build_technical_daily_history_cache_key(code4)
        cached = dataframe_from_cache_payload(self.file_cache.get(key, TECH_DAILY_HISTORY_TTL_SEC))
        if cached is not None:
            return cached
        frame = self.fetch_daily_history(code4)
        self.file_cache.set(key, dataframe_to_cache_payload(frame))
        return frame

    def fetch_intraday_history_cached(self, code4: str) -> pd.DataFrame:
        key = build_technical_intraday_history_cache_key(code4)
        cached = dataframe_from_cache_payload(self.file_cache.get(key, TECH_INTRADAY_HISTORY_TTL_SEC))
        if cached is not None:
            return cached
        frame = self.fetch_intraday_history(code4)
        self.file_cache.set(key, dataframe_to_cache_payload(frame))
        return frame


def _as_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "TechnicalAnalysisResult",
    "TechnicalAnalysisService",
    "dataframe_from_cache_payload",
    "dataframe_to_cache_payload",
]

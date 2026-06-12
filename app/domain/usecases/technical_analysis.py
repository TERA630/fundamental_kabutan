"""Domain use-case: orchestration for technical analysis output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

import pandas as pd

from app.domain.models.market_data import MarketDataBundle
from app.domain.models.technical_snapshot import TechnicalSnapshot
from app.domain.policies.market_history import (
    TECH_DAILY_HISTORY_TTL_SEC,
    TECH_INTRADAY_HISTORY_TTL_SEC,
    build_daily_reference_vwap_snapshot,
    build_intraday_vwap_snapshot,
    build_previous_session_intraday_snapshot,
    build_technical_daily_history_cache_key,
    build_technical_intraday_history_cache_key,
)
from app.domain.policies.technical_indicators import build_technical_snapshot, normalize_daily_history


class TechnicalHistoryCachePort(Protocol):
    def get(self, key: str, ttl_sec: int) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...


TechnicalHistoryProvider = Callable[[str], pd.DataFrame]


@dataclass(frozen=True)
class TechnicalMomentumSession:
    session_date: str | None
    high_breakout: bool | None
    low_higher: bool | None
    volume_vs_avg20_pct: float | None


@dataclass(frozen=True)
class TechnicalThreeSessionMomentum:
    sessions: tuple[TechnicalMomentumSession, TechnicalMomentumSession, TechnicalMomentumSession]
    change_pct: float | None


@dataclass(frozen=True)
class TechnicalAnalysisResult:
    name: str
    code4: str
    snapshot: TechnicalSnapshot
    intraday_price_timestamp: str | None
    three_session_momentum: TechnicalThreeSessionMomentum
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
        if fetch_daily_history is None or fetch_intraday_history is None:
            raise ValueError("TechnicalAnalysisService requires history providers")
        self.fetch_daily_history = fetch_daily_history
        self.fetch_intraday_history = fetch_intraday_history

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
            three_session_momentum=build_three_session_momentum(daily_history),
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


def build_three_session_momentum(history: pd.DataFrame) -> TechnicalThreeSessionMomentum:
    daily = normalize_daily_history(history)
    volume_avg20 = daily["Volume"].rolling(20).mean()
    target_positions = (-4, -3, -2)
    sessions = tuple(_build_momentum_session(daily, volume_avg20, position) for position in target_positions)
    return TechnicalThreeSessionMomentum(
        sessions=sessions,
        change_pct=_three_session_change_pct(daily),
    )


def _build_momentum_session(daily: pd.DataFrame, volume_avg20: pd.Series, position: int) -> TechnicalMomentumSession:
    absolute_position = len(daily) + position
    if absolute_position < 0 or absolute_position >= len(daily):
        return TechnicalMomentumSession(
            session_date=None,
            high_breakout=None,
            low_higher=None,
            volume_vs_avg20_pct=None,
        )

    row = daily.iloc[absolute_position]
    previous_row = daily.iloc[absolute_position - 1] if absolute_position >= 1 else None
    previous_three = daily.iloc[absolute_position - 3 : absolute_position] if absolute_position >= 3 else pd.DataFrame()
    average_volume = _as_float(volume_avg20.iloc[absolute_position])
    volume = _as_float(row["Volume"])
    timestamp = pd.Timestamp(daily.index[absolute_position])
    return TechnicalMomentumSession(
        session_date=timestamp.date().isoformat(),
        high_breakout=_high_breakout(_as_float(row["High"]), previous_three),
        low_higher=_low_higher(_as_float(row["Low"]), previous_row),
        volume_vs_avg20_pct=None if volume is None or average_volume in (None, 0) else (volume / average_volume) * 100,
    )


def _three_session_change_pct(daily: pd.DataFrame) -> float | None:
    if len(daily) < 4:
        return None
    start_close = _as_float(daily.iloc[-4]["Close"])
    end_close = _as_float(daily.iloc[-2]["Close"])
    if start_close in (None, 0) or end_close is None:
        return None
    return ((end_close / start_close) - 1) * 100


def _high_breakout(high: float | None, previous_three: pd.DataFrame) -> bool | None:
    if high is None or len(previous_three) < 3:
        return None
    previous_high = _as_float(previous_three["High"].max())
    return None if previous_high is None else high > previous_high


def _low_higher(low: float | None, previous_row: pd.Series | None) -> bool | None:
    if low is None or previous_row is None:
        return None
    previous_low = _as_float(previous_row["Low"])
    return None if previous_low is None else low > previous_low


def _as_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


__all__ = [
    "TechnicalAnalysisResult",
    "TechnicalAnalysisService",
    "TechnicalMomentumSession",
    "TechnicalThreeSessionMomentum",
    "build_three_session_momentum",
    "dataframe_from_cache_payload",
    "dataframe_to_cache_payload",
]

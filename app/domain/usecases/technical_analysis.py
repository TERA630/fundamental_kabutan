"""Domain use-case: orchestration for technical analysis output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol

import pandas as pd

from app.domain.models.manual_technical_quote import ManualTechnicalQuote
from app.domain.models.market_data import MarketDataBundle
from app.domain.models.rsi_analysis import RsiAnalysis
from app.domain.models.technical_snapshot import TechnicalSnapshot
from app.domain.policies.market_history import (
    TECH_DAILY_HISTORY_TTL_SEC,
    TECH_INTRADAY_HISTORY_TTL_SEC,
    build_daily_reference_vwap_snapshot,
    build_intraday_vwap_snapshot,
    build_previous_session_intraday_snapshot,
    build_technical_daily_history_cache_key,
    build_technical_intraday_history_cache_key,
    normalize_history_frame,
    slice_technical_histories_for_evaluation,
)
from app.domain.policies.technical_indicators import build_technical_snapshot, normalize_daily_history
from app.domain.policies.rsi_analysis import build_rsi_analysis
from app.domain.usecases.market_data_lock import INTRADAY_MARKET_DATA_LOCK, is_intraday_history_consistent


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
    vwap_snapshot: dict[str, float | str | bool | int | None]
    previous_intraday_snapshot: dict[str, float | str | bool | None]
    evaluation_price: float | None
    evaluation_price_source: str
    evaluation_price_timestamp: str | None
    evaluation_at: datetime | None = None
    rsi_analysis: RsiAnalysis | None = None


def dataframe_to_cache_payload(
    frame: pd.DataFrame,
    *,
    code4: str | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "index": [str(value) for value in frame.index],
        "columns": list(frame.columns),
        "data": frame.astype(object).where(pd.notna(frame), None).values.tolist(),
    }
    if code4 is not None:
        payload["code4"] = code4
    if kind is not None:
        payload["kind"] = kind
    return payload


def dataframe_from_cache_payload(
    payload: Any,
    *,
    code4: str | None = None,
    kind: str | None = None,
) -> pd.DataFrame | None:
    if not isinstance(payload, dict):
        return None
    if code4 is not None and payload.get("code4") != code4:
        return None
    if kind is not None and payload.get("kind") != kind:
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

    def build_analysis_result(
        self,
        *,
        name: str,
        code4: str,
        evaluation_at: datetime | None = None,
        manual_quote: ManualTechnicalQuote | None = None,
    ) -> TechnicalAnalysisResult:
        daily_history = self.fetch_daily_history_cached(code4)
        intraday_history = self.fetch_intraday_history_cached(code4, daily_history=daily_history)
        return self.build_analysis_result_from_histories(
            name=name,
            code4=code4,
            daily_history=daily_history,
            intraday_history=intraday_history,
            evaluation_at=evaluation_at,
            manual_quote=manual_quote,
        )

    @staticmethod
    def build_analysis_result_from_bundle(
        *,
        name: str,
        bundle: MarketDataBundle,
        evaluation_at: datetime | None = None,
        manual_quote: ManualTechnicalQuote | None = None,
    ) -> TechnicalAnalysisResult:
        return TechnicalAnalysisService.build_analysis_result_from_histories(
            name=name,
            code4=bundle.code4,
            daily_history=bundle.daily_history,
            intraday_history=bundle.intraday_history,
            evaluation_at=evaluation_at,
            manual_quote=manual_quote,
        )

    @staticmethod
    def build_analysis_result_from_histories(
        *,
        name: str,
        code4: str,
        daily_history: pd.DataFrame,
        intraday_history: pd.DataFrame,
        evaluation_at: datetime | None = None,
        manual_quote: ManualTechnicalQuote | None = None,
    ) -> TechnicalAnalysisResult:
        if manual_quote is not None and evaluation_at is not None:
            raise ValueError("手入力値は過去の評価時点には適用できません。評価時点を最新にしてください。")
        daily_history, intraday_history = slice_technical_histories_for_evaluation(
            daily_history,
            intraday_history,
            evaluation_at,
        )
        if manual_quote is not None:
            daily_history = _apply_manual_quote_to_daily_history(
                daily_history,
                intraday_history,
                manual_quote,
            )
        snapshot = build_technical_snapshot(daily_history)
        vwap_snapshot = (
            build_intraday_vwap_snapshot(intraday_history)
            if not intraday_history.empty
            else build_daily_reference_vwap_snapshot(daily_history)
        )
        if manual_quote is not None:
            vwap_snapshot = _apply_manual_quote_to_vwap_snapshot(vwap_snapshot, manual_quote)
        previous_intraday_snapshot = build_previous_session_intraday_snapshot(daily_history, intraday_history)
        rsi_analysis = build_rsi_analysis(intraday_history)
        if manual_quote is None:
            evaluation_price, evaluation_price_source, evaluation_price_timestamp = _build_evaluation_price(
                daily_history=daily_history,
                intraday_history=intraday_history,
                snapshot=snapshot,
                vwap_snapshot=vwap_snapshot,
            )
        else:
            evaluation_price = manual_quote.latest
            evaluation_price_source = "manual"
            evaluation_price_timestamp = _format_manual_quote_timestamp(manual_quote)
        return TechnicalAnalysisResult(
            name=name,
            code4=code4,
            snapshot=snapshot,
            intraday_price_timestamp=_as_optional_str(vwap_snapshot.get("latest_price_timestamp")),
            three_session_momentum=build_three_session_momentum(daily_history),
            vwap_snapshot=vwap_snapshot,
            previous_intraday_snapshot=previous_intraday_snapshot,
            evaluation_price=evaluation_price,
            evaluation_price_source=evaluation_price_source,
            evaluation_price_timestamp=evaluation_price_timestamp,
            evaluation_at=evaluation_at,
            rsi_analysis=rsi_analysis,
        )

    def fetch_daily_history_cached(self, code4: str) -> pd.DataFrame:
        key = build_technical_daily_history_cache_key(code4)
        cached = dataframe_from_cache_payload(
            self.file_cache.get(key, TECH_DAILY_HISTORY_TTL_SEC),
            code4=code4,
            kind="technical_daily",
        )
        if cached is not None:
            return cached
        frame = self.fetch_daily_history(code4)
        self.file_cache.set(key, dataframe_to_cache_payload(frame, code4=code4, kind="technical_daily"))
        return frame

    def fetch_intraday_history_cached(
        self,
        code4: str,
        *,
        daily_history: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        key = build_technical_intraday_history_cache_key(code4)
        with INTRADAY_MARKET_DATA_LOCK:
            cached = dataframe_from_cache_payload(
                self.file_cache.get(key, TECH_INTRADAY_HISTORY_TTL_SEC),
                code4=code4,
                kind="technical_intraday_5m",
            )
            if cached is not None and is_intraday_history_consistent(cached, daily_history):
                return cached
            frame = self.fetch_intraday_history(code4)
            if not is_intraday_history_consistent(frame, daily_history):
                frame = self.fetch_intraday_history(code4)
            if not is_intraday_history_consistent(frame, daily_history):
                frame = pd.DataFrame()
            self.file_cache.set(
                key,
                dataframe_to_cache_payload(frame, code4=code4, kind="technical_intraday_5m"),
            )
            return frame


def _apply_manual_quote_to_daily_history(
    daily_history: pd.DataFrame,
    intraday_history: pd.DataFrame,
    quote: ManualTechnicalQuote,
) -> pd.DataFrame:
    daily = normalize_history_frame(daily_history)
    if daily.empty:
        raise ValueError("手入力値を反映するための日足データがありません。")

    target_date = quote.observed_at.date()
    positions = [position for position, value in enumerate(daily.index) if pd.Timestamp(value).date() == target_date]
    if positions:
        if positions[-1] != len(daily) - 1:
            raise ValueError("手入力日は最新の日足日付と一致していません。")
        result = daily.copy()
        target_position = positions[-1]
    else:
        if pd.Timestamp(daily.index[-1]).date() > target_date:
            raise ValueError("手入力日は最新の日足日付より前です。")
        intraday = normalize_history_frame(intraday_history)
        target_session = intraday[
            pd.Series(intraday.index.date, index=intraday.index) == target_date
        ]
        if target_session.empty:
            raise ValueError(
                "手入力日のyFinance日足・5分足がありません。市場データを取得してから再実行してください。"
            )
        result = daily[pd.Series(daily.index.date, index=daily.index) < target_date].copy()
        result.loc[pd.Timestamp(target_date), :] = {
            "Open": _as_float(target_session.iloc[0]["Open"]),
            "High": quote.high,
            "Low": quote.low,
            "Close": quote.latest,
            "Volume": _as_float(target_session["Volume"].sum()),
        }
        target_position = len(result) - 1

    open_value = _as_float(result.iloc[target_position]["Open"])
    if open_value is not None and not quote.low <= open_value <= quote.high:
        raise ValueError("当日高値・安値にはyFinanceの当日始値も含まれるように入力してください。")

    result.iloc[target_position, result.columns.get_loc("High")] = quote.high
    result.iloc[target_position, result.columns.get_loc("Low")] = quote.low
    result.iloc[target_position, result.columns.get_loc("Close")] = quote.latest
    return result


def _apply_manual_quote_to_vwap_snapshot(
    vwap_snapshot: dict[str, float | str | bool | int | None],
    quote: ManualTechnicalQuote,
) -> dict[str, float | str | bool | int | None]:
    timestamp = _format_manual_quote_timestamp(quote)
    result = dict(vwap_snapshot)
    result.update(
        {
            "latest": quote.latest,
            "high": quote.high,
            "low": quote.low,
            "vwap": quote.vwap,
            "latest_bar_time": quote.observed_at.strftime("%H:%M"),
            "latest_price_source": "manual",
            "latest_price_timestamp": timestamp,
            "vwap_timestamp": timestamp,
            "manual_override": True,
        }
    )
    return result


def _format_manual_quote_timestamp(quote: ManualTechnicalQuote) -> str:
    return quote.observed_at.strftime("%Y-%m-%d %H:%M")


def _as_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _build_evaluation_price(
    *,
    daily_history: pd.DataFrame,
    intraday_history: pd.DataFrame,
    snapshot: TechnicalSnapshot,
    vwap_snapshot: dict[str, Any],
) -> tuple[float | None, str, str | None]:
    daily = normalize_history_frame(daily_history)
    intraday = normalize_history_frame(intraday_history)
    intraday = intraday[intraday["Volume"] > 0]
    if not daily.empty and not intraday.empty:
        daily_date = pd.Timestamp(daily.index[-1]).date()
        latest_intraday_timestamp = pd.Timestamp(intraday.index[-1])
        intraday_date = latest_intraday_timestamp.date()
        market_closed = latest_intraday_timestamp.time() >= pd.Timestamp("15:25").time()
        intraday_price = _as_float(vwap_snapshot.get("latest"))
        if daily_date == intraday_date:
            if intraday_price is not None and not market_closed:
                return (
                    intraday_price,
                    "intraday_5m",
                    _as_optional_str(vwap_snapshot.get("latest_price_timestamp")),
                )
        elif intraday_date > daily_date and intraday_price is not None:
            return (
                intraday_price,
                "provisional_close" if market_closed else "intraday_5m",
                _as_optional_str(vwap_snapshot.get("latest_price_timestamp")),
            )
    daily_timestamp = None
    if not daily.empty:
        daily_timestamp = f"{pd.Timestamp(daily.index[-1]).date().isoformat()} 終値"
    return snapshot.price.close, "daily_close", daily_timestamp


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

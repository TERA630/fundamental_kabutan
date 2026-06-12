"""Default dependency wiring for analysis application services."""

from __future__ import annotations

from app.data.file_cache import FileCache
from app.data.kabutan_repository import KabutanForecastRepository
from app.data.market_data_provider import (
    fetch_yfinance_analyst_estimates,
    fetch_yfinance_daily_history,
    fetch_yfinance_intraday_history,
    fetch_yfinance_market_snapshot,
    fetch_yfinance_snapshot,
)
from app.domain.models.market_data import MarketDataBundle
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.domain.usecases.kabutan_forecast import FetchKabutanForecastUseCase
from app.domain.usecases.market_data import MarketDataService
from app.domain.usecases.technical_analysis import TechnicalAnalysisService


def build_default_fundamental_service(file_cache: FileCache) -> FundamentalAnalysisService:
    kabutan_repository = KabutanForecastRepository(file_cache=file_cache)
    return FundamentalAnalysisService(
        file_cache=file_cache,
        fetch_market_snapshot=fetch_yfinance_snapshot,
        fetch_analyst_estimates=fetch_yfinance_analyst_estimates,
        fetch_kabutan_forecast_usecase=FetchKabutanForecastUseCase(
            repository=kabutan_repository
        ),
    )


def build_default_technical_service(file_cache: FileCache) -> TechnicalAnalysisService:
    return TechnicalAnalysisService(
        file_cache=file_cache,
        fetch_daily_history=fetch_yfinance_daily_history,
        fetch_intraday_history=fetch_yfinance_intraday_history,
    )


def build_default_market_data_service(file_cache: FileCache) -> MarketDataService:
    return MarketDataService(
        file_cache=file_cache,
        fetch_daily_history=fetch_yfinance_daily_history,
        fetch_intraday_history=fetch_yfinance_intraday_history,
        fetch_market_snapshot=fetch_yfinance_market_snapshot,
    )


def build_default_fundamental_service_with_market_bundle(
    *,
    file_cache: FileCache,
    bundle: MarketDataBundle,
) -> FundamentalAnalysisService:
    kabutan_repository = KabutanForecastRepository(file_cache=file_cache)

    def fetch_market_snapshot(code4: str):
        if code4 == bundle.code4:
            return bundle.snapshot.to_dict()
        return fetch_yfinance_snapshot(code4)

    return FundamentalAnalysisService(
        file_cache=file_cache,
        fetch_market_snapshot=fetch_market_snapshot,
        fetch_analyst_estimates=fetch_yfinance_analyst_estimates,
        fetch_kabutan_forecast_usecase=FetchKabutanForecastUseCase(
            repository=kabutan_repository
        ),
    )


__all__ = [
    "build_default_fundamental_service",
    "build_default_fundamental_service_with_market_bundle",
    "build_default_market_data_service",
    "build_default_technical_service",
]

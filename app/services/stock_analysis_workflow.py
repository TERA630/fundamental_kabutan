"""Workflow for building per-stock analysis outputs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

from app.data.file_cache import FileCache
from app.domain.builders.technical_output import build_technical_output
from app.domain.models.market_data import MarketDataBundle
from app.domain.usecases.fundamental_analysis import (
    FundamentalAnalysisService,
    build_output_from_analysis_result,
)
from app.domain.usecases.technical_analysis import TechnicalAnalysisService
from app.presenters import build_fundamental_output
from app.services.institutional_summary_service import InstitutionalSummaryService


class FetchMarketDataBundle(Protocol):
    def __call__(self, code4: str, *, use_memory_cache: bool = True) -> MarketDataBundle: ...


class StockAnalysisWorkflow:
    def __init__(
        self,
        *,
        file_cache: FileCache,
        build_fundamental_service: Callable[[FileCache], FundamentalAnalysisService],
        build_technical_service: Callable[[FileCache], TechnicalAnalysisService],
        uses_default_fundamental_service: bool,
        uses_default_technical_service: bool,
        fetch_market_data_bundle: FetchMarketDataBundle,
        build_fundamental_service_with_market_bundle: Callable[[MarketDataBundle], FundamentalAnalysisService],
    ):
        self.file_cache = file_cache
        self.build_fundamental_service = build_fundamental_service
        self.build_technical_service = build_technical_service
        self.uses_default_fundamental_service = uses_default_fundamental_service
        self.uses_default_technical_service = uses_default_technical_service
        self.fetch_market_data_bundle = fetch_market_data_bundle
        self.build_fundamental_service_with_market_bundle = build_fundamental_service_with_market_bundle

    def fetch_analysis_output(
        self,
        *,
        name: str,
        code4: str,
        kabutan_html_dir: Path | None = None,
    ) -> str:
        service = self._build_fundamental_service(code4)
        build_analysis_result = getattr(service, "build_analysis_result", None)
        if callable(build_analysis_result):
            result = build_analysis_result(name, code4, kabutan_html_dir=kabutan_html_dir)
            return build_output_from_analysis_result(result, build_fundamental_output)
        return service.build_analysis_output(
                name,
                code4,
                build_output_fn=build_fundamental_output,
                kabutan_html_dir=kabutan_html_dir,
            )

    def build_technical_summary_result(
        self,
        name: str,
        code4: str,
        *,
        evaluation_at: datetime | None = None,
    ):
        if self.uses_default_technical_service:
            bundle = self.fetch_market_data_bundle(
                code4,
                use_memory_cache=evaluation_at is not None,
            )
            return TechnicalAnalysisService.build_analysis_result_from_bundle(
                name=name,
                bundle=bundle,
                evaluation_at=evaluation_at,
            )
        service = self.build_technical_service(self.file_cache)
        if evaluation_at is None:
            return service.build_analysis_result(name=name, code4=code4)
        return service.build_analysis_result(name=name, code4=code4, evaluation_at=evaluation_at)

    def fetch_technical_output(
        self,
        *,
        name: str,
        code4: str,
        evaluation_at: datetime | None = None,
    ) -> str:
        return build_technical_output(
            self.build_technical_summary_result(name=name, code4=code4, evaluation_at=evaluation_at)
        )

    def fetch_institutional_summary_text(
        self,
        *,
        name: str,
        code4: str,
        kabutan_html_dir: Path | None = None,
    ) -> str:
        service = InstitutionalSummaryService(
            file_cache=self.file_cache,
            build_fundamental_service=self.build_fundamental_service,
            build_technical_service=self.build_technical_service,
            uses_default_fundamental_service=self.uses_default_fundamental_service,
            uses_default_technical_service=self.uses_default_technical_service,
            fetch_market_data_bundle=self.fetch_market_data_bundle,
            build_fundamental_service_with_market_bundle=self.build_fundamental_service_with_market_bundle,
        )
        return service.build_text(name=name, code4=code4, kabutan_html_dir=kabutan_html_dir)

    def _build_fundamental_service(self, code4: str) -> FundamentalAnalysisService:
        if self.uses_default_fundamental_service:
            bundle = self.fetch_market_data_bundle(code4)
            return self.build_fundamental_service_with_market_bundle(bundle)
        return self.build_fundamental_service(self.file_cache)


__all__ = ["StockAnalysisWorkflow"]

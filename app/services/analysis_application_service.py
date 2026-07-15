"""Application service for shared analysis workflows."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Callable

from app.data.file_cache import FileCache
from app.domain.models.manual_technical_quote import ManualTechnicalQuote
from app.domain.models.market_data import MarketDataBundle
from app.domain.models.watchlist import WatchlistEntry
from app.domain.policies.market_history import build_intraday_evaluation_timestamps
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.domain.usecases.kabutan_html_dir import ResolvedKabutanHtmlDir
from app.domain.usecases.market_data import MarketDataService
from app.domain.usecases.technical_analysis import TechnicalAnalysisService
from app.domain.usecases.watchlist_path import ResolvedWatchlistPath
from app.services.analysis_service_factory import (
    build_default_fundamental_service,
    build_default_fundamental_service_with_market_bundle,
    build_default_market_data_service,
    build_default_technical_service,
    build_default_us_market_summary_service,
)
from app.services.cache_service import CacheService
from app.services.analysis_output_workflow import AnalysisOutputResult, AnalysisOutputWorkflow
from app.services.kabutan_html_dir_service import KabutanHtmlDirService
from app.services.kabutan_html_package_service import KabutanHtmlPackageService
from app.services.kabutan_package_workflow import (
    KabutanHtmlPackageImportResult,
    KabutanHtmlPackageInspectionResult,
    KabutanHtmlPackageResult,
    KabutanPackageResolution,
    KabutanPackageWorkflow,
)
from app.services.summary_workflow import (
    FUNDAMENTAL_SUMMARY_FILENAME_PREFIX,
    TECHNICAL_SUMMARY_FILENAME_PREFIX,
    SummaryWorkflow,
    build_fundamental_summary_filename,
    build_technical_summary_filename,
)
from app.services.stock_analysis_workflow import StockAnalysisWorkflow
from app.services.ui_resource_workflow import UiResourceWorkflow
from app.services.watchlist_service import WatchlistService


class AnalysisApplicationService:
    """Application service shared by GUI and Web entry points."""

    def __init__(
        self,
        file_cache: FileCache | None = None,
        build_fundamental_service: Callable[[FileCache], FundamentalAnalysisService] | None = None,
        build_technical_service: Callable[[FileCache], TechnicalAnalysisService] | None = None,
        build_market_data_service: Callable[[FileCache], MarketDataService] | None = None,
    ):
        self.file_cache = file_cache or FileCache()
        self.cache_service = CacheService(self.file_cache)
        self.watchlist_service = WatchlistService(self.cache_service)
        self.kabutan_html_dir_service = KabutanHtmlDirService(self.cache_service)
        self.kabutan_html_package_service = KabutanHtmlPackageService()
        self._uses_default_fundamental_service = build_fundamental_service is None
        self._uses_default_technical_service = build_technical_service is None
        self.build_fundamental_service = build_fundamental_service or build_default_fundamental_service
        self.build_technical_service = build_technical_service or build_default_technical_service
        self.build_market_data_service = build_market_data_service or build_default_market_data_service
        self._market_data_bundle_cache: dict[str, MarketDataBundle] = {}
        self.stock_analysis_workflow = StockAnalysisWorkflow(
            file_cache=self.file_cache,
            build_fundamental_service=self.build_fundamental_service,
            build_technical_service=self.build_technical_service,
            uses_default_fundamental_service=self._uses_default_fundamental_service,
            uses_default_technical_service=self._uses_default_technical_service,
            fetch_market_data_bundle=self.fetch_market_data_bundle,
            build_fundamental_service_with_market_bundle=self._build_default_fundamental_service_with_market_bundle,
        )
        self.kabutan_package_workflow = KabutanPackageWorkflow(
            file_cache=self.file_cache,
            package_service=self.kabutan_html_package_service,
            save_kabutan_html_dir_cache=self.save_kabutan_html_dir_cache,
        )
        self.ui_resource_workflow = UiResourceWorkflow(
            cache_service=self.cache_service,
            watchlist_service=self.watchlist_service,
            kabutan_html_dir_service=self.kabutan_html_dir_service,
        )
        self.analysis_output_workflow = AnalysisOutputWorkflow(
            fetch_technical_output=self.fetch_technical_output,
            fetch_analysis_output=self.fetch_analysis_output,
            fetch_institutional_summary_text=self.fetch_institutional_summary_text,
        )
        self.summary_workflow = SummaryWorkflow(
            file_cache=self.file_cache,
            build_fundamental_service=self.build_fundamental_service,
            build_technical_summary_result=self.stock_analysis_workflow.build_technical_summary_result,
            build_us_market_summary=build_default_us_market_summary_service().build_summary_table,
        )

    def fetch_market_data_bundle(
        self,
        code4: str,
        *,
        use_memory_cache: bool = True,
        evaluation_at: datetime | None = None,
    ) -> MarketDataBundle:
        if evaluation_at is not None:
            return self.build_market_data_service(self.file_cache).fetch_bundle(
                code4,
                evaluation_date=evaluation_at.date(),
            )
        cached = self._market_data_bundle_cache.get(code4)
        if use_memory_cache and cached is not None:
            return cached
        bundle = self.build_market_data_service(self.file_cache).fetch_bundle(code4)
        self._market_data_bundle_cache[code4] = bundle
        return bundle

    def _build_default_fundamental_service_with_market_bundle(self, bundle: MarketDataBundle) -> FundamentalAnalysisService:
        return build_default_fundamental_service_with_market_bundle(
            file_cache=self.file_cache,
            bundle=bundle,
        )

    def fetch_resolved_kabutan_html_dir(self) -> ResolvedKabutanHtmlDir:
        return self.ui_resource_workflow.fetch_resolved_kabutan_html_dir()

    def save_kabutan_html_dir_cache(self, path: Path) -> None:
        self.ui_resource_workflow.save_kabutan_html_dir_cache(path)

    def fetch_kabutan_package_zip_cache(self) -> Path | None:
        return self.ui_resource_workflow.fetch_kabutan_package_zip_cache()

    def save_kabutan_package_zip_cache(self, path: Path) -> None:
        self.ui_resource_workflow.save_kabutan_package_zip_cache(path)

    def clear_kabutan_package_zip_cache(self) -> None:
        self.ui_resource_workflow.clear_kabutan_package_zip_cache()

    def build_kabutan_html_package(
        self,
        *,
        source_dir: Path,
        output_dir: Path | None = None,
    ) -> KabutanHtmlPackageResult:
        return self.kabutan_package_workflow.build_package(
            source_dir=source_dir,
            output_dir=output_dir,
        )

    def import_kabutan_html_package(
        self,
        *,
        zip_path: Path,
        output_dir: Path | None = None,
    ) -> KabutanHtmlPackageImportResult:
        return self.kabutan_package_workflow.import_package_to_default_dir(
            zip_path=zip_path,
            output_dir=output_dir,
        )

    def inspect_kabutan_html_package(self, *, zip_path: Path) -> KabutanHtmlPackageInspectionResult:
        return self.kabutan_package_workflow.inspect_package(zip_path=zip_path)

    def build_file_signature(self, path: Path) -> tuple[int, str]:
        return self.kabutan_package_workflow.build_file_signature(path)

    def import_output_dir_for_signature(self, signature: tuple[int, str]) -> Path:
        return self.kabutan_package_workflow.import_output_dir_for_signature(signature)

    def html_dir_ready(self, html_dir: Path) -> bool:
        return self.kabutan_package_workflow.html_dir_ready(html_dir)

    def resolve_imported_kabutan_package(
        self,
        *,
        zip_path: Path,
        current_signature: tuple[int, str] | tuple[int, int] | None,
        current_html_dir: Path | None,
    ) -> KabutanPackageResolution:
        return self.kabutan_package_workflow.resolve_imported_package(
            zip_path=zip_path,
            current_signature=current_signature,
            current_html_dir=current_html_dir,
        )

    def fetch_resolved_watchlist_path(self) -> ResolvedWatchlistPath:
        return self.ui_resource_workflow.fetch_resolved_watchlist_path()

    def save_watchlist_path_cache(self, path: Path) -> None:
        self.ui_resource_workflow.save_watchlist_path_cache(path)

    def fetch_watchlist_entries(self, path: Path) -> list[tuple[str, str]]:
        return self.ui_resource_workflow.fetch_watchlist_entries(path)

    def fetch_watchlist_entries_with_sectors(self, path: Path) -> list[WatchlistEntry]:
        return self.ui_resource_workflow.fetch_watchlist_entries_with_sectors(path)

    def fetch_analysis_output(
        self,
        *,
        name: str,
        code4: str,
        kabutan_html_dir: Path | None = None,
    ) -> str:
        return self.stock_analysis_workflow.fetch_analysis_output(
            name=name,
            code4=code4,
            kabutan_html_dir=kabutan_html_dir,
        )

    def fetch_output_for_mode(
        self,
        *,
        name: str,
        code4: str,
        mode: str,
        kabutan_html_dir: Path | None = None,
        evaluation_at: datetime | None = None,
    ) -> AnalysisOutputResult:
        return self.analysis_output_workflow.fetch_output_for_mode(
            name=name,
            code4=code4,
            mode=mode,
            kabutan_html_dir=kabutan_html_dir,
            evaluation_at=evaluation_at,
        )

    def build_fundamental_summary_table(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        kabutan_html_dir: Path | None = None,
    ):
        return self.summary_workflow.build_fundamental_summary_table(
            watchlist_entries=watchlist_entries,
            kabutan_html_dir=kabutan_html_dir,
        )

    def build_and_save_fundamental_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        output_dir: Path,
        kabutan_html_dir: Path | None = None,
        today: date | None = None,
    ) -> Path:
        return self.summary_workflow.build_and_save_fundamental_summary(
            watchlist_entries=watchlist_entries,
            output_dir=output_dir,
            kabutan_html_dir=kabutan_html_dir,
            today=today,
        )

    def build_technical_summary_table(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        evaluation_at: datetime | None = None,
    ):
        return self.summary_workflow.build_technical_summary_table(
            watchlist_entries=watchlist_entries,
            evaluation_at=evaluation_at,
        )

    def build_technical_sector_breadth_output(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        code4: str,
        evaluation_at: datetime | None = None,
        prebuilt_results: dict[str, object] | None = None,
    ) -> str:
        return self.summary_workflow.build_technical_sector_breadth_output(
            watchlist_entries=watchlist_entries,
            code4=code4,
            evaluation_at=evaluation_at,
            prebuilt_results=prebuilt_results,
        )

    def build_summary_table_for_mode(
        self,
        *,
        mode: str,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        kabutan_html_dir: Path | None = None,
        evaluation_at: datetime | None = None,
    ):
        return self.summary_workflow.build_summary_table_for_mode(
            mode=mode,
            watchlist_entries=watchlist_entries,
            kabutan_html_dir=kabutan_html_dir,
            evaluation_at=evaluation_at,
        )

    def build_and_save_technical_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        output_dir: Path,
        generated_at: datetime | None = None,
        evaluation_at: datetime | None = None,
    ) -> Path:
        return self.summary_workflow.build_and_save_technical_summary(
            watchlist_entries=watchlist_entries,
            output_dir=output_dir,
            generated_at=generated_at,
            evaluation_at=evaluation_at,
        )

    def fetch_technical_output(
        self,
        *,
        name: str,
        code4: str,
        evaluation_at: datetime | None = None,
        manual_quote: ManualTechnicalQuote | None = None,
    ) -> str:
        return self.stock_analysis_workflow.fetch_technical_output(
            name=name,
            code4=code4,
            evaluation_at=evaluation_at,
            manual_quote=manual_quote,
        )

    def fetch_technical_output_result(
        self,
        *,
        name: str,
        code4: str,
        evaluation_at: datetime | None = None,
        manual_quote: ManualTechnicalQuote | None = None,
    ):
        return self.stock_analysis_workflow.fetch_technical_output_result(
            name=name,
            code4=code4,
            evaluation_at=evaluation_at,
            manual_quote=manual_quote,
        )

    def fetch_technical_evaluation_dates(self, code4: str) -> tuple[date, ...]:
        service = self.build_market_data_service(self.file_cache)
        return service.fetch_evaluation_dates(code4)

    def fetch_technical_evaluation_timestamps(
        self,
        code4: str,
        evaluation_date: date | None = None,
    ) -> tuple[datetime, ...]:
        if evaluation_date is not None:
            service = self.build_market_data_service(self.file_cache)
            history = service.fetch_historical_intraday_history_cached(code4, evaluation_date)
            return build_intraday_evaluation_timestamps(history)
        bundle = self.fetch_market_data_bundle(
            code4,
            use_memory_cache=False,
        )
        return build_intraday_evaluation_timestamps(bundle.intraday_history)

    def fetch_institutional_summary_text(
        self,
        *,
        name: str,
        code4: str,
        kabutan_html_dir: Path | None = None,
    ) -> str:
        return self.stock_analysis_workflow.fetch_institutional_summary_text(
            name=name,
            code4=code4,
            kabutan_html_dir=kabutan_html_dir,
        )


__all__ = [
    "FUNDAMENTAL_SUMMARY_FILENAME_PREFIX",
    "TECHNICAL_SUMMARY_FILENAME_PREFIX",
    "AnalysisApplicationService",
    "AnalysisOutputResult",
    "KabutanPackageResolution",
    "build_default_fundamental_service",
    "build_default_market_data_service",
    "build_default_technical_service",
    "build_default_us_market_summary_service",
    "build_fundamental_summary_filename",
    "build_technical_summary_filename",
]

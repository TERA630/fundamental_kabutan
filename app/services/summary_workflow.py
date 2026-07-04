"""Workflow for building and saving analysis summaries."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Callable

from app.data.file_cache import FileCache
from app.domain.builders.fundamental_summary import build_fundamental_summary_markdown
from app.domain.builders.hybrid_summary import build_hybrid_summary_markdown
from app.domain.builders.sector_breadth_output import build_single_stock_sector_breadth_text
from app.domain.builders.technical_summary import build_technical_summary_markdown
from app.domain.models.watchlist import WatchlistEntry
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.domain.usecases.fundamental_summary import FundamentalSummaryService
from app.domain.usecases.hybrid_summary import HybridSummaryService
from app.domain.usecases.technical_summary import TechnicalSummaryService

FUNDAMENTAL_SUMMARY_FILENAME_PREFIX = "fundamental_summary"
HYBRID_SUMMARY_FILENAME_PREFIX = "hybrid_summary"
TECHNICAL_SUMMARY_FILENAME_PREFIX = "technical_summary"


def build_fundamental_summary_filename(*, today: date | None = None) -> str:
    target_date = today or date.today()
    return f"{FUNDAMENTAL_SUMMARY_FILENAME_PREFIX}-{target_date.isoformat()}.md"


def build_technical_summary_filename(*, generated_at: datetime | None = None) -> str:
    target = generated_at or datetime.now()
    return f"{TECHNICAL_SUMMARY_FILENAME_PREFIX}_{target.strftime('%m-%d-%H-%M')}.md"


def build_hybrid_summary_filename(*, generated_at: datetime | None = None) -> str:
    target = generated_at or datetime.now()
    return f"{HYBRID_SUMMARY_FILENAME_PREFIX}_{target.strftime('%m-%d-%H-%M')}.md"


def _watchlist_tuples(watchlist_entries: list[tuple[str, str] | WatchlistEntry]) -> list[tuple[str, str]]:
    return [entry.as_tuple() if isinstance(entry, WatchlistEntry) else entry for entry in watchlist_entries]


def _sectors_for_code4(watchlist_entries: list[tuple[str, str] | WatchlistEntry], code4: str) -> tuple[str, ...]:
    sectors: list[str] = []
    for entry in watchlist_entries:
        if not isinstance(entry, WatchlistEntry) or entry.code4 != code4:
            continue
        for sector in entry.sectors:
            if sector not in sectors:
                sectors.append(sector)
    return tuple(sectors)


def _entries_for_sectors(
    watchlist_entries: list[tuple[str, str] | WatchlistEntry],
    sectors: tuple[str, ...],
) -> list[WatchlistEntry]:
    filtered: list[WatchlistEntry] = []
    for entry in watchlist_entries:
        if not isinstance(entry, WatchlistEntry):
            continue
        matching_sectors = tuple(sector for sector in entry.sectors if sector in sectors)
        if matching_sectors:
            filtered.append(WatchlistEntry(name=entry.name, code4=entry.code4, sectors=matching_sectors))
    return filtered


class SummaryWorkflow:
    def __init__(
        self,
        *,
        file_cache: FileCache,
        build_fundamental_service: Callable[[FileCache], FundamentalAnalysisService],
        build_technical_summary_result: Callable[[str, str], object],
        build_us_market_summary: Callable[[], object] | None = None,
    ):
        self.file_cache = file_cache
        self.build_fundamental_service = build_fundamental_service
        self.build_technical_summary_result = build_technical_summary_result
        self.build_us_market_summary = build_us_market_summary

    def build_fundamental_summary_table(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        kabutan_html_dir: Path | None = None,
    ):
        service = FundamentalSummaryService(self.build_fundamental_service(self.file_cache))
        return service.build_summary_table(_watchlist_tuples(watchlist_entries), kabutan_html_dir=kabutan_html_dir)

    def build_technical_summary_table(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        evaluation_at: datetime | None = None,
    ):
        build_result = self.build_technical_summary_result
        if evaluation_at is not None:
            build_result = lambda name, code4: self.build_technical_summary_result(
                name,
                code4,
                evaluation_at=evaluation_at,
            )
        service = TechnicalSummaryService(
            build_result,
            build_us_market_summary=self.build_us_market_summary,
        )
        return service.build_summary_table(watchlist_entries)

    def build_technical_sector_breadth_output(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        code4: str,
        evaluation_at: datetime | None = None,
        prebuilt_results: dict[str, object] | None = None,
    ) -> str:
        sectors = _sectors_for_code4(watchlist_entries, code4)
        if not sectors:
            return ""
        sector_entries = _entries_for_sectors(watchlist_entries, sectors)
        if not sector_entries:
            return ""
        prebuilt_results = prebuilt_results or {}
        build_result = self.build_technical_summary_result
        if evaluation_at is not None:
            build_result = lambda name, code4: self.build_technical_summary_result(
                name,
                code4,
                evaluation_at=evaluation_at,
            )

        def build_result_with_prebuilt(name: str, code4: str):
            if code4 in prebuilt_results:
                return prebuilt_results[code4]
            return build_result(name, code4)

        table = TechnicalSummaryService(
            build_result_with_prebuilt,
            build_us_market_summary=None,
        ).build_summary_table(
            sector_entries,
        )
        return build_single_stock_sector_breadth_text(table.sector_breadth, sectors)

    def build_summary_table_for_mode(
        self,
        *,
        mode: str,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        kabutan_html_dir: Path | None = None,
        evaluation_at: datetime | None = None,
    ):
        if mode == "technical":
            return self.build_technical_summary_table(
                watchlist_entries=watchlist_entries,
                evaluation_at=evaluation_at,
            )
        return self.build_fundamental_summary_table(
            watchlist_entries=watchlist_entries,
            kabutan_html_dir=kabutan_html_dir,
        )

    def build_hybrid_summary_table(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        kabutan_html_dir: Path | None = None,
        evaluation_at: datetime | None = None,
    ):
        fundamental_table = self.build_fundamental_summary_table(
            watchlist_entries=watchlist_entries,
            kabutan_html_dir=kabutan_html_dir,
        )
        technical_table = self.build_technical_summary_table(
            watchlist_entries=watchlist_entries,
            evaluation_at=evaluation_at,
        )
        return HybridSummaryService().build_summary_table(
            fundamental_table=fundamental_table,
            technical_table=technical_table,
        )

    def build_and_save_fundamental_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        output_dir: Path,
        kabutan_html_dir: Path | None = None,
        today: date | None = None,
    ) -> Path:
        table = self.build_fundamental_summary_table(
            watchlist_entries=watchlist_entries,
            kabutan_html_dir=kabutan_html_dir,
        )
        markdown = build_fundamental_summary_markdown(table)
        output_path = output_dir / build_fundamental_summary_filename(today=today)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    def build_and_save_technical_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        output_dir: Path,
        generated_at: datetime | None = None,
        evaluation_at: datetime | None = None,
    ) -> Path:
        table = self.build_technical_summary_table(
            watchlist_entries=watchlist_entries,
            evaluation_at=evaluation_at,
        )
        markdown = build_technical_summary_markdown(table)
        output_path = output_dir / build_technical_summary_filename(generated_at=generated_at)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path

    def build_and_save_hybrid_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str] | WatchlistEntry],
        output_dir: Path,
        kabutan_html_dir: Path | None = None,
        generated_at: datetime | None = None,
        evaluation_at: datetime | None = None,
    ) -> Path:
        table = self.build_hybrid_summary_table(
            watchlist_entries=watchlist_entries,
            kabutan_html_dir=kabutan_html_dir,
            evaluation_at=evaluation_at,
        )
        markdown = build_hybrid_summary_markdown(table)
        output_path = output_dir / build_hybrid_summary_filename(generated_at=generated_at)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path


__all__ = [
    "FUNDAMENTAL_SUMMARY_FILENAME_PREFIX",
    "HYBRID_SUMMARY_FILENAME_PREFIX",
    "TECHNICAL_SUMMARY_FILENAME_PREFIX",
    "SummaryWorkflow",
    "build_fundamental_summary_filename",
    "build_hybrid_summary_filename",
    "build_technical_summary_filename",
]

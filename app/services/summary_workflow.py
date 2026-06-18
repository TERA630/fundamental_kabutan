"""Workflow for building and saving analysis summaries."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Callable

from app.data.file_cache import FileCache
from app.domain.builders.fundamental_summary import build_fundamental_summary_markdown
from app.domain.builders.technical_summary import build_technical_summary_markdown
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.domain.usecases.fundamental_summary import FundamentalSummaryService
from app.domain.usecases.technical_summary import TechnicalSummaryService

FUNDAMENTAL_SUMMARY_FILENAME_PREFIX = "fundamental_summary"
TECHNICAL_SUMMARY_FILENAME_PREFIX = "technical_summary"


def build_fundamental_summary_filename(*, today: date | None = None) -> str:
    target_date = today or date.today()
    return f"{FUNDAMENTAL_SUMMARY_FILENAME_PREFIX}-{target_date.isoformat()}.md"


def build_technical_summary_filename(*, generated_at: datetime | None = None) -> str:
    target = generated_at or datetime.now()
    return f"{TECHNICAL_SUMMARY_FILENAME_PREFIX}_{target.strftime('%m-%d-%H-%M')}.md"


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
        watchlist_entries: list[tuple[str, str]],
        kabutan_html_dir: Path | None = None,
    ):
        service = FundamentalSummaryService(self.build_fundamental_service(self.file_cache))
        return service.build_summary_table(watchlist_entries, kabutan_html_dir=kabutan_html_dir)

    def build_technical_summary_table(
        self,
        *,
        watchlist_entries: list[tuple[str, str]],
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

    def build_summary_table_for_mode(
        self,
        *,
        mode: str,
        watchlist_entries: list[tuple[str, str]],
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

    def build_and_save_fundamental_summary(
        self,
        *,
        watchlist_entries: list[tuple[str, str]],
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
        watchlist_entries: list[tuple[str, str]],
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


__all__ = [
    "FUNDAMENTAL_SUMMARY_FILENAME_PREFIX",
    "TECHNICAL_SUMMARY_FILENAME_PREFIX",
    "SummaryWorkflow",
    "build_fundamental_summary_filename",
    "build_technical_summary_filename",
]

"""GUI controller: UIイベントからユースケース呼び出しを仲介する。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from app.data.file_cache import FileCache
from app.data.kabutan_repository import KabutanForecastRepository
from app.data.market_data_provider import fetch_yfinance_snapshot
from app.data.watchlist_repository import fetch_watchlist_entries
from app.domain.usecases.kabutan_html_dir import ResolveKabutanHtmlDirUseCase, ResolvedKabutanHtmlDir
from app.domain.usecases.kabutan_forecast import FetchKabutanForecastUseCase
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.presenters import build_fundamental_output


def build_default_fundamental_service(file_cache: FileCache) -> FundamentalAnalysisService:
    kabutan_repository = KabutanForecastRepository(file_cache=file_cache)
    return FundamentalAnalysisService(
        file_cache=file_cache,
        fetch_market_snapshot=fetch_yfinance_snapshot,
        fetch_kabutan_forecast_usecase=FetchKabutanForecastUseCase(
            repository=kabutan_repository
        ),
    )


class FundamentalGuiController:
    """GUI層コントローラー: 表示以外のオーケストレーションを担当。"""

    def __init__(
        self,
        file_cache: FileCache | None = None,
        build_fundamental_service: Callable[[FileCache], FundamentalAnalysisService] | None = None,
    ):
        self.file_cache = file_cache or FileCache()
        self.resolve_kabutan_html_dir_usecase = ResolveKabutanHtmlDirUseCase()
        self.build_fundamental_service = build_fundamental_service or build_default_fundamental_service

    def fetch_resolved_kabutan_html_dir(self) -> ResolvedKabutanHtmlDir:
        cached_dir = self.file_cache.fetch_kabutan_html_dir_cache()
        return self.resolve_kabutan_html_dir_usecase.fetch_resolved_kabutan_html_dir(cached_dir)

    def save_kabutan_html_dir_cache(self, path: Path) -> None:
        self.file_cache.save_kabutan_html_dir_cache(path)

    def fetch_watchlist_entries(self, path: Path) -> list[tuple[str, str]]:
        return fetch_watchlist_entries(path)

    def fetch_analysis_output(
        self,
        *,
        name: str,
        code4: str,
        output_cache: dict[str, str],
        output_cache_key: str,
        kabutan_html_dir: Path | None = None,
    ) -> str:
        cached_output = output_cache.get(output_cache_key)
        if cached_output is not None:
            return cached_output

        service = self.build_fundamental_service(self.file_cache)
        output = service.build_analysis_output(
            name,
            code4,
            build_output_fn=build_fundamental_output,
            kabutan_html_dir=kabutan_html_dir,
        )
        output_cache[output_cache_key] = output
        return output


__all__ = ["FundamentalGuiController"]

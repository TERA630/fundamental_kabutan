"""Domain use-case: orchestration for fundamental analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol
from pathlib import Path
import re
import inspect

from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_balance_sheet import KabutanBalanceSheetRow
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.quarterly_financials import QuarterlyActual, QuarterlyMetricRow
from app.domain.usecases.quarterly_financial_table import BuildQuarterlyFinancialTableUseCase
from app.domain.policies.financial_rows import FinancialRowCandidate, select_common_financial_rows
from app.domain.usecases.kabutan_forecast import FetchKabutanForecastUseCase

CACHE_TTL_YF_SEC = 12 * 60 * 60
MARKET_SNAPSHOT_KEYS = (
    "price",
    "market_cap",
    "per",
    "pbr",
    "industry",
    "div_yield",
    "payout_ratio",
)


class MarketDataProviderPort(Protocol):
    def __call__(self, code4: str) -> dict[str, float | str | None]: ...


class MarketSnapshotCachePort(Protocol):
    def get(self, key: str, ttl_sec: int) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...


def build_empty_market_snapshot() -> dict[str, float | str | None]:
    return {key: None for key in MARKET_SNAPSHOT_KEYS}


def normalize_market_snapshot(snapshot: dict[str, Any]) -> dict[str, float | str | None]:
    return {key: snapshot.get(key) for key in MARKET_SNAPSHOT_KEYS}


class KabutanForecastRepositoryPort(Protocol):

    def fetch_kabutan_forecast_pair(
        self, code: str, target_years: tuple[int, int] | None = None
    ) -> KabutanForecastPair: ...

    def fetch_kabutan_forecast_pair_from_file(
        self, html_path: str | Path, target_years: tuple[int, int] | None = None
    ) -> KabutanForecastPair: ...

    def fetch_kabutan_cashflow_rows_from_file(self, html_path: str | Path) -> tuple[KabutanCashflowRow, ...]: ...

    def fetch_kabutan_balance_sheet_rows_from_file(self, html_path: str | Path) -> tuple[KabutanBalanceSheetRow, ...]: ...

    def fetch_kabutan_quarterly_actual_rows_from_file(self, html_path: str | Path, *, ticker: str) -> tuple[QuarterlyActual, ...]: ...


@dataclass(frozen=True)
class KabutanFetchResult:
    pair: KabutanForecastPair | None
    source: str
    cashflow_rows: tuple[KabutanCashflowRow, ...] = ()
    message: str | None = None
    balance_sheet_rows: tuple[KabutanBalanceSheetRow, ...] = ()
    quarterly_actual_rows: tuple[QuarterlyActual, ...] = ()
    quarterly_message: str | None = None


class FundamentalAnalysisService:
    """ドメイン層ユースケース: 分析出力の組み立て実行を担当。"""

    def __init__(
        self,
        file_cache: MarketSnapshotCachePort,
        fetch_market_snapshot: MarketDataProviderPort,
        fetch_kabutan_forecast_usecase: FetchKabutanForecastUseCase | None = None,
    ):
        self.cache = file_cache
        self.fetch_market_snapshot = fetch_market_snapshot
        self.fetch_kabutan_forecast_usecase = fetch_kabutan_forecast_usecase

    def build_cache_key_price_snapshot(self, code4: str) -> str:
        return f"yf_{code4}"

    def fetch_price_snapshot(self, code4: str) -> dict[str, float | str | None]:
        cache_key = self.build_cache_key_price_snapshot(code4)
        cached = self.cache.get(cache_key, CACHE_TTL_YF_SEC)
        if isinstance(cached, dict):
            return normalize_market_snapshot(cached)

        snapshot = self.fetch_market_snapshot(code4)
        if isinstance(snapshot, dict) and snapshot.get("price") is not None:
            self.cache.set(cache_key, snapshot)
            return normalize_market_snapshot(snapshot)
        return build_empty_market_snapshot()

    def build_analysis_output(
        self,
        name: str,
        code4: str,
        build_output_fn: Callable[..., str],
        kabutan_html_dir: Path | None = None,
    ) -> str:
        master: dict[str, Any] | None = None
        price_snapshot = self.fetch_price_snapshot(code4)
        kabutan_fetch_result = self.fetch_kabutan_forecast_pair(
            code4,
            html_dir=kabutan_html_dir,
        )
        output_context = {
            "name": name,
            "code4": code4,
            "master": master,
            "price": price_snapshot.get("price"),
            "market_cap": price_snapshot.get("market_cap"),
            "market_snapshot": price_snapshot,
            "kabutan_forecast_pair": kabutan_fetch_result.pair,
            "kabutan_cashflow_rows": kabutan_fetch_result.cashflow_rows,
            "kabutan_source": kabutan_fetch_result.source,
            "kabutan_source_message": kabutan_fetch_result.message,
            "financial_metric_rows": self.build_financial_metric_rows(
                price=price_snapshot.get("price"),
                forecast_pair=kabutan_fetch_result.pair,
                balance_sheet_rows=kabutan_fetch_result.balance_sheet_rows,
            ),
            "quarterly_metric_rows": self.build_quarterly_metric_rows(
                code4=code4,
                rows=kabutan_fetch_result.quarterly_actual_rows,
                forecast_pair=kabutan_fetch_result.pair,
            ),
            "quarterly_message": kabutan_fetch_result.quarterly_message,
        }
        accepted_params = inspect.signature(build_output_fn).parameters
        safe_context = {key: value for key, value in output_context.items() if key in accepted_params}
        return build_output_fn(**safe_context)


    @staticmethod
    def build_quarterly_metric_rows(
        *,
        code4: str,
        rows: tuple[QuarterlyActual, ...],
        forecast_pair: KabutanForecastPair | None,
    ) -> tuple[QuarterlyMetricRow, ...]:
        if not rows:
            return ()
        fiscal_end_month = FundamentalAnalysisService.resolve_fiscal_end_month_from_forecast_pair(forecast_pair)
        if fiscal_end_month is None:
            fiscal_end_month = max((row.quarter_end_month for row in rows if row.quarter_end_month is not None), default=None)
        usecase = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=fiscal_end_month, max_quarters=5)
        return usecase.execute(rows)

    @staticmethod
    def resolve_fiscal_end_month_from_forecast_pair(forecast_pair: KabutanForecastPair | None) -> int | None:
        if forecast_pair is None:
            return None
        rows = list(forecast_pair.all_rows) if forecast_pair.all_rows else [
            row
            for row in (
                forecast_pair.previous2_actual,
                forecast_pair.previous_actual,
                forecast_pair.current_actual,
                forecast_pair.current_forecast,
                forecast_pair.next_forecast,
            )
            if row is not None
        ]
        if not rows:
            return None
        # 通期業績テーブルの決算月（YYYY.MM の MM）を採用
        return rows[-1].month

    @staticmethod
    def build_financial_metric_rows(
        *,
        price: float | None,
        forecast_pair: KabutanForecastPair | None,
        balance_sheet_rows: tuple[KabutanBalanceSheetRow, ...],
    ) -> tuple[FinancialMetricInputRow, ...]:
        if forecast_pair is None or not forecast_pair.all_rows or not balance_sheet_rows:
            return ()

        forecast_by_year: dict[int, tuple[int | None, int | None]] = {}
        for row in forecast_pair.all_rows:
            if row.section != "実績":
                continue
            forecast_by_year[row.year] = (row.final_profit, row.operating_profit)

        candidates: list[FinancialRowCandidate] = []
        by_year_bs: dict[int, list[KabutanBalanceSheetRow]] = {}
        for bs_row in balance_sheet_rows:
            by_year_bs.setdefault(bs_row.year, []).append(bs_row)

        selected_bs_by_year: dict[int, KabutanBalanceSheetRow] = {
            year: max(rows, key=lambda r: r.month) for year, rows in by_year_bs.items()
        }

        for year, bs_row in selected_bs_by_year.items():
            final_profit, operating_profit = forecast_by_year.get(year, (None, None))
            interest_bearing_debt: int | None = None
            if bs_row.equity is not None and bs_row.interest_bearing_debt_multiple is not None:
                interest_bearing_debt = int(round(bs_row.equity * bs_row.interest_bearing_debt_multiple))
            candidates.append(
                FinancialRowCandidate(
                    year=year,
                    net_income=final_profit,
                    equity=bs_row.equity,
                    operating_profit=operating_profit,
                    interest_bearing_debt=interest_bearing_debt,
                    bps=bs_row.bps,
                )
            )

        selected = select_common_financial_rows(candidates, max_years=3)

        out: list[FinancialMetricInputRow] = []
        for row in selected:
            out.append(
                FinancialMetricInputRow(
                    year=row.year,
                    net_income=row.net_income,
                    equity=row.equity,
                    operating_profit=row.operating_profit,
                    interest_bearing_debt=row.interest_bearing_debt,
                    bps=row.bps,
                    price=price,
                )
            )
        return tuple(out)

    def fetch_kabutan_forecast_pair(
        self,
        code4: str,
        html_dir: Path | None = None,
        allow_kabutan_web_fallback: bool = False,
    ) -> KabutanFetchResult:
        if html_dir is None:
            if allow_kabutan_web_fallback:
                repository = self._get_kabutan_repository()
                return self._fetch_kabutan_forecast_pair_from_web(repository, code4)
            return KabutanFetchResult(pair=None, source="none", message="HTMLフォルダ未設定")

        repository = self._get_kabutan_repository()
        html_candidates = self._build_kabutan_html_candidates(code4=code4, html_dir=html_dir)
        for html_path in html_candidates:
            if html_path.exists():
                try:
                    pair = repository.fetch_kabutan_forecast_pair_from_file(html_path)
                    try:
                        cashflow_rows = repository.fetch_kabutan_cashflow_rows_from_file(html_path)
                    except Exception:
                        cashflow_rows = ()
                    try:
                        balance_sheet_rows = repository.fetch_kabutan_balance_sheet_rows_from_file(html_path)
                    except Exception:
                        balance_sheet_rows = ()
                    try:
                        quarterly_actual_rows = repository.fetch_kabutan_quarterly_actual_rows_from_file(html_path, ticker=code4)
                        quarterly_message: str | None = None
                    except Exception as exc:
                        quarterly_actual_rows = ()
                        quarterly_message = f"四半期業績推移の解析失敗: {exc}"
                    return KabutanFetchResult(
                        pair=pair,
                        cashflow_rows=cashflow_rows,
                        balance_sheet_rows=balance_sheet_rows,
                        quarterly_actual_rows=quarterly_actual_rows,
                        quarterly_message=quarterly_message,
                        source="html",
                    )
                except Exception:
                    continue

        if allow_kabutan_web_fallback:
            return self._fetch_kabutan_forecast_pair_from_web(repository, code4)
        if html_candidates:
            return KabutanFetchResult(pair=None, source="none", message="HTML解析に失敗")
        return KabutanFetchResult(pair=None, source="none", message="HTMLファイル未検出")

    def _get_kabutan_repository(self) -> KabutanForecastRepositoryPort:
        if self.fetch_kabutan_forecast_usecase is None:
            raise RuntimeError("Kabutan forecast use case is not configured")
        return self.fetch_kabutan_forecast_usecase.repository

    @staticmethod
    def _fetch_kabutan_forecast_pair_from_web(repository: KabutanForecastRepositoryPort, code4: str) -> KabutanFetchResult:
        try:
            return KabutanFetchResult(pair=repository.fetch_kabutan_forecast_pair(code4), source="web")
        except Exception as exc:
            return KabutanFetchResult(pair=None, source="none", message=f"Web取得失敗: {exc}")

    @staticmethod
    def _build_kabutan_html_candidates(code4: str, html_dir: Path) -> list[Path]:
        direct_candidates = [html_dir / f"{code4}.html", html_dir / f"{code4}.htm"]
        regex = re.compile(rf"(?<!\d){re.escape(code4)}(?!\d)")
        matched_candidates = sorted(
            [
                path
                for path in html_dir.iterdir()
                if path.is_file()
                and path.suffix.lower() in {".html", ".htm"}
                and regex.search(path.stem) is not None
            ]
        )

        candidates: list[Path] = []
        for path in [*direct_candidates, *matched_candidates]:
            if path not in candidates:
                candidates.append(path)
        return candidates


__all__ = ["FundamentalAnalysisService"]

"""Domain use-case: orchestration for fundamental analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol
from pathlib import Path
import re
import inspect

from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_balance_sheet import KabutanBalanceSheetRow
from app.domain.models.analyst_estimates import AnalystEstimates
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.market_data import MARKET_SNAPSHOT_KEYS, MarketSnapshot
from app.domain.models.cf_scoring_input import CfScoringInput
from app.domain.models.cf_scoring_result import CfScoringResult
from app.domain.models.quarterly_financials import QuarterlyActual, QuarterlyMetricRow
from app.domain.usecases import fundamental_calculations as calculations
from app.domain.usecases.kabutan_forecast import FetchKabutanForecastUseCase
from app.domain.policies.cf_scoring import calculate_cf_score
from app.domain.policies.growth_phase import GrowthPhase
from app.domain.policies.valuation_levels import PerLevel, RoicLevel

CACHE_TTL_YF_SEC = 12 * 60 * 60


class MarketDataProviderPort(Protocol):
    def __call__(self, code4: str) -> dict[str, float | str | None] | MarketSnapshot: ...


class AnalystEstimatesProviderPort(Protocol):
    def __call__(self, code4: str) -> AnalystEstimates: ...


class MarketSnapshotCachePort(Protocol):
    def get(self, key: str, ttl_sec: int) -> Any: ...

    def set(self, key: str, value: Any) -> None: ...


def build_empty_market_snapshot() -> dict[str, float | str | None]:
    return MarketSnapshot.empty().to_dict()


def normalize_market_snapshot(snapshot: Mapping[str, Any] | MarketSnapshot) -> dict[str, float | str | None]:
    if isinstance(snapshot, MarketSnapshot):
        return snapshot.to_dict()
    return MarketSnapshot.from_mapping(snapshot).to_dict()


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


@dataclass(frozen=True)
class FundamentalAnalysisResult:
    name: str
    code4: str
    master: dict[str, Any] | None
    price_snapshot: dict[str, float | str | None]
    analyst_estimates: AnalystEstimates
    kabutan_fetch_result: KabutanFetchResult
    financial_metric_rows: tuple[FinancialMetricInputRow, ...]
    quarterly_metric_rows: tuple[QuarterlyMetricRow, ...]
    cf_scoring_input: CfScoringInput | None
    cf_scoring_result: CfScoringResult | None
    growth_phase: GrowthPhase | None
    per_level: PerLevel | None
    roic_level: RoicLevel | None
    operating_profit_cagr_3y: float | None

    def to_output_context(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "code4": self.code4,
            "master": self.master,
            "price": self.price_snapshot.get("price"),
            "market_cap": self.price_snapshot.get("market_cap"),
            "market_snapshot": self.price_snapshot,
            "analyst_estimates": self.analyst_estimates,
            "kabutan_forecast_pair": self.kabutan_fetch_result.pair,
            "kabutan_cashflow_rows": self.kabutan_fetch_result.cashflow_rows,
            "kabutan_source": self.kabutan_fetch_result.source,
            "kabutan_source_message": self.kabutan_fetch_result.message,
            "financial_metric_rows": self.financial_metric_rows,
            "quarterly_metric_rows": self.quarterly_metric_rows,
            "quarterly_message": self.kabutan_fetch_result.quarterly_message,
            "cf_scoring_result": self.cf_scoring_result,
            "growth_phase": self.growth_phase,
            "per_level": self.per_level,
            "roic_level": self.roic_level,
            "operating_profit_cagr_3y": self.operating_profit_cagr_3y,
        }


class FundamentalAnalysisService:
    """ドメイン層ユースケース: 分析出力の組み立て実行を担当。"""

    def __init__(
        self,
        file_cache: MarketSnapshotCachePort,
        fetch_market_snapshot: MarketDataProviderPort,
        fetch_analyst_estimates: AnalystEstimatesProviderPort | None = None,
        fetch_kabutan_forecast_usecase: FetchKabutanForecastUseCase | None = None,
    ):
        self.cache = file_cache
        self.fetch_market_snapshot = fetch_market_snapshot
        self.fetch_analyst_estimates = fetch_analyst_estimates or (lambda _code4: AnalystEstimates.empty())
        self.fetch_kabutan_forecast_usecase = fetch_kabutan_forecast_usecase

    def build_cache_key_price_snapshot(self, code4: str) -> str:
        return f"yf_{code4}"

    def build_cache_key_analyst_estimates(self, code4: str) -> str:
        return f"yf_analyst_{code4}"

    def fetch_price_snapshot(self, code4: str) -> dict[str, float | str | None]:
        cache_key = self.build_cache_key_price_snapshot(code4)
        cached = self.cache.get(cache_key, CACHE_TTL_YF_SEC)
        if isinstance(cached, dict):
            return normalize_market_snapshot(cached)

        snapshot = self.fetch_market_snapshot(code4)
        normalized = normalize_market_snapshot(snapshot) if isinstance(snapshot, (dict, MarketSnapshot)) else build_empty_market_snapshot()
        if normalized.get("price") is not None:
            self.cache.set(cache_key, normalized)
            return normalized
        return build_empty_market_snapshot()

    def fetch_cached_analyst_estimates(self, code4: str) -> AnalystEstimates:
        cache_key = self.build_cache_key_analyst_estimates(code4)
        cached = self.cache.get(cache_key, CACHE_TTL_YF_SEC)
        if isinstance(cached, dict):
            return AnalystEstimates.from_mapping(cached)

        estimates = self.fetch_analyst_estimates(code4)
        self.cache.set(cache_key, estimates.to_dict())
        return estimates

    def build_analysis_result(
        self,
        name: str,
        code4: str,
        kabutan_html_dir: Path | None = None,
    ) -> FundamentalAnalysisResult:
        master: dict[str, Any] | None = None
        price_snapshot = self.fetch_price_snapshot(code4)
        analyst_estimates = self.fetch_cached_analyst_estimates(code4)
        kabutan_fetch_result = self.fetch_kabutan_forecast_pair(
            code4,
            html_dir=kabutan_html_dir,
        )
        financial_metric_rows = self.build_financial_metric_rows(
            price=price_snapshot.get("price"),
            forecast_pair=kabutan_fetch_result.pair,
            balance_sheet_rows=kabutan_fetch_result.balance_sheet_rows,
        )
        cf_scoring_input = self.build_cf_scoring_input(
            code4=code4,
            as_of=self.resolve_cf_scoring_as_of(
                price_snapshot=price_snapshot,
                forecast_pair=kabutan_fetch_result.pair,
            ),
            price=price_snapshot.get("price"),
            market_per=price_snapshot.get("per"),
            market_cap=price_snapshot.get("market_cap"),
            forecast_pair=kabutan_fetch_result.pair,
            cashflow_rows=kabutan_fetch_result.cashflow_rows,
            financial_metric_rows=financial_metric_rows,
        )
        cf_scoring_result = calculate_cf_score(cf_scoring_input) if cf_scoring_input is not None else None
        quarterly_metric_rows = self.build_quarterly_metric_rows(
            code4=code4,
            rows=kabutan_fetch_result.quarterly_actual_rows,
            forecast_pair=kabutan_fetch_result.pair,
        )

        return FundamentalAnalysisResult(
            name=name,
            code4=code4,
            master=master,
            price_snapshot=price_snapshot,
            analyst_estimates=analyst_estimates,
            kabutan_fetch_result=kabutan_fetch_result,
            financial_metric_rows=financial_metric_rows,
            quarterly_metric_rows=quarterly_metric_rows,
            cf_scoring_input=cf_scoring_input,
            cf_scoring_result=cf_scoring_result,
            growth_phase=self.build_growth_phase(kabutan_fetch_result.pair),
            per_level=self.build_per_level(
                cf_scoring_input=cf_scoring_input,
                industry=price_snapshot.get("industry"),
            ),
            roic_level=self.build_roic_level(cf_scoring_input),
            operating_profit_cagr_3y=calculations.calculate_operating_profit_cagr_3y(kabutan_fetch_result.pair),
        )

    def build_analysis_output(
        self,
        name: str,
        code4: str,
        build_output_fn: Callable[..., str],
        kabutan_html_dir: Path | None = None,
    ) -> str:
        """Compatibility wrapper around ``build_analysis_result``.

        New callers should prefer building a FundamentalAnalysisResult and formatting it
        explicitly with build_output_from_analysis_result.
        """

        result = self.build_analysis_result(name, code4, kabutan_html_dir=kabutan_html_dir)
        return build_output_from_analysis_result(result, build_output_fn)

    @staticmethod
    def resolve_cf_scoring_as_of(
        *,
        price_snapshot: dict[str, float | str | None],
        forecast_pair: KabutanForecastPair | None,
    ) -> str | None:
        return calculations.resolve_cf_scoring_as_of(
            price_snapshot=price_snapshot,
            forecast_pair=forecast_pair,
        )

    @staticmethod
    def build_quarterly_metric_rows(
        *,
        code4: str,
        rows: tuple[QuarterlyActual, ...],
        forecast_pair: KabutanForecastPair | None,
    ) -> tuple[QuarterlyMetricRow, ...]:
        return calculations.build_quarterly_metric_rows(
            code4=code4,
            rows=rows,
            forecast_pair=forecast_pair,
        )

    @staticmethod
    def resolve_fiscal_end_month_from_forecast_pair(forecast_pair: KabutanForecastPair | None) -> int | None:
        return calculations.resolve_fiscal_end_month_from_forecast_pair(forecast_pair)

    @staticmethod
    def build_financial_metric_rows(
        *,
        price: float | None,
        forecast_pair: KabutanForecastPair | None,
        balance_sheet_rows: tuple[KabutanBalanceSheetRow, ...],
    ) -> tuple[FinancialMetricInputRow, ...]:
        return calculations.build_financial_metric_rows(
            price=price,
            forecast_pair=forecast_pair,
            balance_sheet_rows=balance_sheet_rows,
        )

    @staticmethod
    def build_growth_phase(forecast_pair: KabutanForecastPair | None) -> GrowthPhase | None:
        return calculations.build_growth_phase(forecast_pair)

    @staticmethod
    def build_per_level(*, cf_scoring_input: CfScoringInput | None, industry: float | str | None) -> PerLevel | None:
        return calculations.build_per_level(cf_scoring_input=cf_scoring_input, industry=industry)

    @staticmethod
    def build_roic_level(cf_scoring_input: CfScoringInput | None) -> RoicLevel | None:
        return calculations.build_roic_level(cf_scoring_input)

    @staticmethod
    def build_cf_scoring_input(
        *,
        code4: str,
        as_of: str | None,
        price: float | None,
        market_per: float | str | None,
        market_cap: float | str | None,
        forecast_pair: KabutanForecastPair | None,
        cashflow_rows: tuple[KabutanCashflowRow, ...],
        financial_metric_rows: tuple[FinancialMetricInputRow, ...],
    ) -> CfScoringInput | None:
        return calculations.build_cf_scoring_input(
            code4=code4,
            as_of=as_of,
            price=price,
            market_per=market_per,
            market_cap=market_cap,
            forecast_pair=forecast_pair,
            cashflow_rows=cashflow_rows,
            financial_metric_rows=financial_metric_rows,
        )

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


def build_output_from_analysis_result(
    result: FundamentalAnalysisResult,
    build_output_fn: Callable[..., str],
) -> str:
    output_context = result.to_output_context()
    signature = inspect.signature(build_output_fn)
    accepts_var_keyword = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    if accepts_var_keyword:
        return build_output_fn(**output_context)

    accepted_params = signature.parameters
    safe_context = {key: value for key, value in output_context.items() if key in accepted_params}
    return build_output_fn(**safe_context)


__all__ = [
    "FundamentalAnalysisResult",
    "FundamentalAnalysisService",
    "KabutanFetchResult",
    "build_output_from_analysis_result",
]

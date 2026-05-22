"""Domain usecases for building display-ready fundamental snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.models.fundamental_display import (
    FundamentalDisplaySnapshot,
    PeriodFundamentalRow,
    PriceSnapshot,
    StockProfile,
    ValuationMetrics,
)


class FundamentalRepositoryPort(Protocol):
    def fetch_stock_profile(self, code4: str) -> StockProfile: ...
    def fetch_fundamental_rows(self, code4: str, years: tuple[int, ...]) -> list[PeriodFundamentalRow]: ...


class MarketRepositoryPort(Protocol):
    def fetch_price_snapshot(self, code4: str) -> PriceSnapshot: ...


class ValuationRepositoryPort(Protocol):
    def fetch_valuation_metrics(self, code4: str, fiscal_year: int, kind: str) -> ValuationMetrics | None: ...


def calc_operating_margin_pct(row: PeriodFundamentalRow) -> float | None:
    sales = row.sales_hundred_million_yen
    op = row.operating_profit_hundred_million_yen
    if sales in (None, 0) or op is None:
        return None
    return op / sales * 100


def calc_ordinary_margin_pct(row: PeriodFundamentalRow) -> float | None:
    sales = row.sales_hundred_million_yen
    ordinary = row.ordinary_profit_hundred_million_yen
    if sales in (None, 0) or ordinary is None:
        return None
    return ordinary / sales * 100


def calc_operating_growth_yoy_pct(current: PeriodFundamentalRow, previous: PeriodFundamentalRow | None) -> float | None:
    if previous is None:
        return None
    current_op = current.operating_profit_hundred_million_yen
    prev_op = previous.operating_profit_hundred_million_yen
    if current_op is None or prev_op in (None, 0):
        return None
    return (current_op / prev_op - 1) * 100


def calc_per_times(price_yen: float | None, eps_yen: float | None) -> float | None:
    if price_yen in (None, 0) or eps_yen in (None, 0):
        return None
    return price_yen / eps_yen


def calc_dividend_yield_pct(price_yen: float | None, dividend_yen: float | None) -> float | None:
    if price_yen in (None, 0) or dividend_yen is None:
        return None
    return dividend_yen / price_yen * 100


def grade_company_scale(market_cap_billion_yen: float | None) -> str | None:
    if market_cap_billion_yen is None:
        return None
    if market_cap_billion_yen >= 100_000:
        return "超大型"
    if market_cap_billion_yen >= 10_000:
        return "大型主役"
    if market_cap_billion_yen >= 3_000:
        return "中型主役"
    if market_cap_billion_yen >= 1_000:
        return "小〜中型"
    return "小型"


@dataclass
class BuildFundamentalDisplaySnapshotUseCase:
    fundamental_repository: FundamentalRepositoryPort
    market_repository: MarketRepositoryPort
    valuation_repository: ValuationRepositoryPort

    def _get_valuation_from_row(self, *, row: PeriodFundamentalRow | None, price_yen: float | None) -> ValuationMetrics | None:
        if row is None:
            return None
        return ValuationMetrics(
            per=calc_per_times(price_yen, row.eps_yen),
            eps_yen=row.eps_yen,
            dividend_yield_pct=calc_dividend_yield_pct(price_yen, row.dividend_yen),
        )

    def get_fundamental_display_snapshot(self, code4: str, base_year: int) -> FundamentalDisplaySnapshot:
        years = (base_year - 2, base_year - 1, base_year, base_year + 1, base_year + 2)
        profile = self.fundamental_repository.fetch_stock_profile(code4)
        price = self.market_repository.fetch_price_snapshot(code4)
        rows = self.fundamental_repository.fetch_fundamental_rows(code4, years)

        normalized_rows: list[PeriodFundamentalRow] = []
        previous_row: PeriodFundamentalRow | None = None
        for row in sorted(rows, key=lambda x: x.fiscal_year):
            op_margin = calc_operating_margin_pct(row)
            ordinary_margin = calc_ordinary_margin_pct(row)
            op_growth = calc_operating_growth_yoy_pct(row, previous_row)
            normalized_rows.append(
                PeriodFundamentalRow(
                    period_kind=row.period_kind,
                    fiscal_year=row.fiscal_year,
                    sales_hundred_million_yen=row.sales_hundred_million_yen,
                    operating_profit_hundred_million_yen=row.operating_profit_hundred_million_yen,
                    ordinary_profit_hundred_million_yen=row.ordinary_profit_hundred_million_yen,
                    final_profit_hundred_million_yen=row.final_profit_hundred_million_yen,
                    eps_yen=row.eps_yen,
                    dividend_yen=row.dividend_yen,
                    operating_margin_pct=op_margin,
                    ordinary_margin_pct=ordinary_margin,
                    operating_growth_yoy_pct=op_growth,
                )
            )
            previous_row = row

        row_by_year = {row.fiscal_year: row for row in normalized_rows}
        metrics_actual = self._get_valuation_from_row(row=row_by_year.get(base_year), price_yen=price.price_yen)
        metrics_current_forecast = self._get_valuation_from_row(row=row_by_year.get(base_year + 1), price_yen=price.price_yen)
        metrics_next_forecast = self._get_valuation_from_row(row=row_by_year.get(base_year + 2), price_yen=price.price_yen)

        return FundamentalDisplaySnapshot(
            profile=StockProfile(
                code4=profile.code4,
                name=profile.name,
                industry_name=profile.industry_name,
                market_cap_billion_yen=profile.market_cap_billion_yen,
                size_class_label=profile.size_class_label or grade_company_scale(profile.market_cap_billion_yen),
            ),
            price=price,
            metrics_actual=metrics_actual,
            metrics_current_forecast=metrics_current_forecast,
            metrics_next_forecast=metrics_next_forecast,
            rows=tuple(normalized_rows),
        )


__all__ = [
    "FundamentalRepositoryPort",
    "MarketRepositoryPort",
    "ValuationRepositoryPort",
    "calc_operating_margin_pct",
    "calc_ordinary_margin_pct",
    "calc_operating_growth_yoy_pct",
    "calc_per_times",
    "calc_dividend_yield_pct",
    "grade_company_scale",
    "BuildFundamentalDisplaySnapshotUseCase",
]

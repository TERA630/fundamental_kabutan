"""Domain builder for Kabutan forecast output section."""

from __future__ import annotations

from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.quarterly_financials import QuarterlyMetricRow
from app.domain.models.cf_scoring_result import CfScoringResult
from app.domain.models.display_sections import (
    CashflowMetricDisplayRow,
    CashflowTimelineSection,
    DisplaySections,
    FinancialMetricDisplayRow,
    FinancialMetricsSection,
    ForecastTableSection,
    GrowthTimelineSection,
    QuarterlyMetricsSection,
    Section,
)
from app.domain.policies.growth_metrics import (
    calc_eps_growth_rate,
    calc_operating_growth_rate,
    calc_cagr,
)
from app.domain.policies.growth_rows import build_growth_rows, select_cagr_row_by_year
from app.domain.policies.financial_metrics import calc_pbr, calc_roe, calc_roic_approx
from app.presentation.display_formatter import format_sections


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _preferred_forecast_row_by_year(rows: list[KabutanForecastRow]) -> dict[int, KabutanForecastRow]:
    by_year: dict[int, list[KabutanForecastRow]] = {}
    for row in rows:
        by_year.setdefault(row.year, []).append(row)
    result: dict[int, KabutanForecastRow] = {}
    for year, candidates in by_year.items():
        result[year] = next((r for r in candidates if r.section == "実績"), candidates[0])
    return result


def _preferred_cashflow_rows(cashflow_rows: tuple[KabutanCashflowRow, ...], max_years: int = 3) -> list[KabutanCashflowRow]:
    by_year: dict[int, list[KabutanCashflowRow]] = {}
    for row in cashflow_rows:
        by_year.setdefault(row.year, []).append(row)

    selected: list[KabutanCashflowRow] = []
    for year in sorted(by_year.keys(), reverse=True)[:max_years]:
        candidates = by_year[year]
        selected.append(max(candidates, key=lambda r: r.month))
    return sorted(selected, key=lambda r: r.year)


def _resolve_fcf_million_yen(cf_row: KabutanCashflowRow) -> int | None:
    if cf_row.free_cf is not None:
        return cf_row.free_cf
    if cf_row.operating_cf is None or cf_row.investing_cf is None:
        return None
    return cf_row.operating_cf + cf_row.investing_cf


def _calc_fcf_yield_pct(free_cf_million_yen: int | None, market_cap_yen: float | None) -> float | None:
    if free_cf_million_yen is None or market_cap_yen in (None, 0):
        return None
    return ((free_cf_million_yen * 1_000_000) / market_cap_yen) * 100


def _build_cashflow_section(rows: list[KabutanForecastRow], cashflow_rows: tuple[KabutanCashflowRow, ...], market_cap: float | None) -> CashflowTimelineSection:
    selected_cashflow_rows = _preferred_cashflow_rows(cashflow_rows, max_years=3)
    if not selected_cashflow_rows:
        return CashflowTimelineSection(actual_rows=[], metric_rows=[])

    forecast_by_year = _preferred_forecast_row_by_year(rows)
    metric_rows: list[CashflowMetricDisplayRow] = []

    for cf_row in selected_cashflow_rows:
        forecast_row = forecast_by_year.get(cf_row.year)
        sales = forecast_row.sales if forecast_row else None
        final_profit = forecast_row.final_profit if forecast_row else None
        operating_cf_margin = _safe_div(cf_row.operating_cf, sales)
        cash_conversion = _safe_div(cf_row.operating_cf, final_profit)
        resolved_fcf = _resolve_fcf_million_yen(cf_row)
        fcf_margin = _safe_div(resolved_fcf, sales)
        fcf_yield_pct = _calc_fcf_yield_pct(resolved_fcf, market_cap)
        investment_aggressiveness_pct = None
        if cf_row.operating_cf not in (None, 0) and cf_row.investing_cf is not None:
            investment_aggressiveness_pct = abs(cf_row.investing_cf) / cf_row.operating_cf * 100

        metric_rows.append(
            CashflowMetricDisplayRow(
                year=cf_row.year,
                cash_conversion_pct=cash_conversion * 100 if cash_conversion is not None else None,
                fcf_yield_pct=fcf_yield_pct,
                fcf_margin_pct=fcf_margin * 100 if fcf_margin is not None else None,
                operating_cf_margin_pct=operating_cf_margin * 100 if operating_cf_margin is not None else None,
                investment_aggressiveness_pct=investment_aggressiveness_pct,
            )
        )

    return CashflowTimelineSection(actual_rows=selected_cashflow_rows, metric_rows=metric_rows)
def _build_financial_section(financial_metric_rows: tuple[FinancialMetricInputRow, ...]) -> FinancialMetricsSection:
    rows: list[FinancialMetricDisplayRow] = []
    for row in financial_metric_rows:
        rows.append(
            FinancialMetricDisplayRow(
                year=row.year,
                roe_pct=calc_roe(row.net_income, row.equity),
                roic_pct=calc_roic_approx(row.operating_profit, row.equity, row.interest_bearing_debt),
                pbr=calc_pbr(row.price, row.bps),
            )
        )
    return FinancialMetricsSection(rows=rows)


def _build_growth_section(rows: list[KabutanForecastRow]) -> GrowthTimelineSection | None:
    if not rows:
        return None

    growth_rows = build_growth_rows(rows)
    operating_growth_rates: list[float | None] = []
    eps_growth_rates: list[float | None] = []

    for index, row in enumerate(growth_rows):
        previous_row = growth_rows[index - 1] if index > 0 else None
        operating_growth_rates.append(
            calc_operating_growth_rate(
                previous_row.operating_profit if previous_row else None,
                row.operating_profit,
            )
        )
        eps_growth_rates.append(
            calc_eps_growth_rate(
                previous_row.revised_eps if previous_row else None,
                row.revised_eps,
            )
        )

    row_by_year = select_cagr_row_by_year(growth_rows)
    if row_by_year:
        cagr_end_year = max(row_by_year.keys())
        cagr_start_year = cagr_end_year - 3
        start_row = row_by_year.get(cagr_start_year)
        end_row = row_by_year.get(cagr_end_year)
        operating_cagr = calc_cagr(
            start_row.operating_profit if start_row else None,
            end_row.operating_profit if end_row else None,
            years=3,
        )
        sales_cagr = calc_cagr(
            start_row.sales if start_row else None,
            end_row.sales if end_row else None,
            years=3,
        )
        eps_cagr = calc_cagr(
            start_row.revised_eps if start_row else None,
            end_row.revised_eps if end_row else None,
            years=3,
        )
    else:
        cagr_start_year = None
        cagr_end_year = None
        sales_cagr = None
        operating_cagr = None
        eps_cagr = None

    return GrowthTimelineSection(
        rows=growth_rows,
        eps_growth_rates=eps_growth_rates,
        operating_growth_rates=operating_growth_rates,
        sales_cagr=sales_cagr,
        operating_cagr=operating_cagr,
        eps_cagr=eps_cagr,
        cagr_start_year=cagr_start_year,
        cagr_end_year=cagr_end_year,
    )


def build_kabutan_forecast_sections(
    kabutan_forecast_pair: KabutanForecastPair | None,
    kabutan_source: str,
    kabutan_source_message: str | None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    market_cap: float | None = None,
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
    quarterly_metric_rows: tuple[QuarterlyMetricRow, ...] = (),
    quarterly_message: str | None = None,
    include_financial_section: bool = True,
) -> DisplaySections:
    rows: list[KabutanForecastRow] = []
    if kabutan_forecast_pair is not None:
        if kabutan_forecast_pair.all_rows:
            rows = list(kabutan_forecast_pair.all_rows)
        else:
            rows = [
                row
                for row in (
                    kabutan_forecast_pair.previous2_actual,
                    kabutan_forecast_pair.previous_actual,
                    kabutan_forecast_pair.current_actual,
                    kabutan_forecast_pair.current_forecast,
                    kabutan_forecast_pair.next_forecast,
                )
                if row is not None
            ]

    sections: list[Section] = [
        ForecastTableSection(kabutan_source, kabutan_source_message, rows),
    ]
    growth_section = _build_growth_section(rows)
    if growth_section is not None:
        sections.append(growth_section)
    sections.append(_build_cashflow_section(rows, kabutan_cashflow_rows, market_cap))
    if include_financial_section:
        sections.append(_build_financial_section(financial_metric_rows))
    sections.append(QuarterlyMetricsSection(rows=list(quarterly_metric_rows), message=quarterly_message))
    return DisplaySections(sections=sections)


def build_kabutan_forecast_output(
    base_output: str,
    kabutan_forecast_pair: KabutanForecastPair | None,
    kabutan_source: str,
    kabutan_source_message: str | None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    market_cap: float | None = None,
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
    quarterly_metric_rows: tuple[QuarterlyMetricRow, ...] = (),
    quarterly_message: str | None = None,
    cf_scoring_result: CfScoringResult | None = None,
    include_financial_section: bool = True,
) -> str:
    sections = build_kabutan_forecast_sections(
        kabutan_forecast_pair,
        kabutan_source,
        kabutan_source_message,
        kabutan_cashflow_rows,
        market_cap,
        financial_metric_rows,
        quarterly_metric_rows,
        quarterly_message,
        include_financial_section,
    )
    section = format_sections(sections)
    return f"{base_output}\n{section}"


__all__ = ["build_kabutan_forecast_output", "build_kabutan_forecast_sections"]

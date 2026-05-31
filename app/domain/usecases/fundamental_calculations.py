"""Pure calculation helpers for fundamental analysis orchestration."""

from __future__ import annotations

from app.domain.models.cf_scoring_input import CfScoringInput
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.models.kabutan_balance_sheet import KabutanBalanceSheetRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair
from app.domain.models.quarterly_financials import QuarterlyActual, QuarterlyMetricRow
from app.domain.policies.financial_metrics import calc_roic_approx
from app.domain.policies.financial_rows import FinancialRowCandidate, select_common_financial_rows
from app.domain.policies.growth_metrics import calc_cagr
from app.domain.policies.growth_rows import build_growth_rows, select_cagr_row_by_year
from app.domain.policies.growth_phase import GrowthPhase, classify_growth_phase_from_rows
from app.domain.policies.valuation_levels import PerLevel, RoicLevel, classify_per_level, classify_roic_level
from app.domain.usecases.quarterly_financial_table import BuildQuarterlyFinancialTableUseCase


def resolve_cf_scoring_as_of(
    *,
    price_snapshot: dict[str, float | str | None],
    forecast_pair: KabutanForecastPair | None,
) -> str | None:
    if forecast_pair is None or not forecast_pair.all_rows:
        return None
    actual_rows = [row for row in forecast_pair.all_rows if row.section == "実績"]
    if actual_rows:
        latest_actual = max(actual_rows, key=lambda row: (row.year, row.month))
        return f"{latest_actual.year}-{latest_actual.month:02d}"

    latest_observed = max(forecast_pair.all_rows, key=lambda row: (row.year, row.month))
    fallback_year = latest_observed.year - 1
    return f"{fallback_year}-{latest_observed.month:02d}"


def build_quarterly_metric_rows(
    *,
    code4: str,
    rows: tuple[QuarterlyActual, ...],
    forecast_pair: KabutanForecastPair | None,
) -> tuple[QuarterlyMetricRow, ...]:
    if not rows:
        return ()
    fiscal_end_month = resolve_fiscal_end_month_from_forecast_pair(forecast_pair)
    if fiscal_end_month is None:
        fiscal_end_month = max((row.quarter_end_month for row in rows if row.quarter_end_month is not None), default=None)
    usecase = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=fiscal_end_month, max_quarters=5)
    return usecase.execute(rows)


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
    return rows[-1].month


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
    return tuple(
        FinancialMetricInputRow(
            year=row.year,
            net_income=row.net_income,
            equity=row.equity,
            operating_profit=row.operating_profit,
            interest_bearing_debt=row.interest_bearing_debt,
            bps=row.bps,
            price=price,
        )
        for row in selected
    )


def build_growth_phase(forecast_pair: KabutanForecastPair | None) -> GrowthPhase | None:
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
    return classify_growth_phase_from_rows(rows)


def _forecast_rows(forecast_pair: KabutanForecastPair) -> list:
    return list(forecast_pair.all_rows) if forecast_pair.all_rows else [
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


def _calculate_growth_score_cagrs(forecast_pair: KabutanForecastPair) -> tuple[float | None, float | None]:
    row_by_year = select_cagr_row_by_year(build_growth_rows(_forecast_rows(forecast_pair)))
    if not row_by_year:
        return None, None

    cagr_end_year = max(row_by_year.keys())
    cagr_start_year = cagr_end_year - 3
    start_row = row_by_year.get(cagr_start_year)
    end_row = row_by_year.get(cagr_end_year)
    return (
        calc_cagr(start_row.revised_eps if start_row else None, end_row.revised_eps if end_row else None, 3),
        calc_cagr(start_row.sales if start_row else None, end_row.sales if end_row else None, 3),
    )


def build_per_level(*, cf_scoring_input: CfScoringInput | None, industry: float | str | None) -> PerLevel | None:
    industry_text = industry if isinstance(industry, str) else None
    per = cf_scoring_input.per if cf_scoring_input is not None else None
    return classify_per_level(per, industry_text)


def build_roic_level(cf_scoring_input: CfScoringInput | None) -> RoicLevel | None:
    roic = cf_scoring_input.roic if cf_scoring_input is not None else None
    return classify_roic_level(roic)


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
    if forecast_pair is None:
        return None

    roic: float | None = None
    if financial_metric_rows:
        latest_fin = max(financial_metric_rows, key=lambda row: row.year)
        roic = calc_roic_approx(latest_fin.operating_profit, latest_fin.equity, latest_fin.interest_bearing_debt)

    actual_rows = [row for row in forecast_pair.all_rows if row.section == "実績"] if forecast_pair.all_rows else []
    latest_actual = max(actual_rows, key=lambda row: (row.year, row.month)) if actual_rows else None

    latest_cf = max(cashflow_rows, key=lambda row: (row.year, row.month)) if cashflow_rows else None
    ocf = latest_cf.operating_cf if latest_cf is not None else None
    fcf = None
    if latest_cf is not None:
        if latest_cf.free_cf is not None:
            fcf = float(latest_cf.free_cf)
        elif latest_cf.operating_cf is not None and latest_cf.investing_cf is not None:
            fcf = float(latest_cf.operating_cf + latest_cf.investing_cf)

    eps_candidates = [
        (forecast_pair.next_forecast.revised_eps if forecast_pair.next_forecast is not None else None),
        forecast_pair.current_forecast.revised_eps,
    ]
    forecast_eps = next((eps for eps in eps_candidates if eps is not None and eps > 0), None)
    per_from_forecast = (float(price) / float(forecast_eps)) if (price is not None and forecast_eps is not None) else None

    per: float | None = per_from_forecast
    if per is None and isinstance(market_per, (int, float)):
        per = float(market_per)

    eps_cagr_3y, sales_cagr_3y = _calculate_growth_score_cagrs(forecast_pair)

    market_cap_float = float(market_cap) if isinstance(market_cap, (int, float)) else None
    fcf_yield = ((fcf * 1_000_000) / market_cap_float) * 100 if fcf is not None and market_cap_float not in (None, 0.0) else None

    return CfScoringInput(
        code4=code4,
        as_of=as_of,
        roic=roic,
        ocf=float(ocf) if ocf is not None else None,
        net_income=float(latest_actual.final_profit) if (latest_actual is not None and latest_actual.final_profit is not None) else None,
        operating_income=float(latest_actual.operating_profit) if (latest_actual is not None and latest_actual.operating_profit is not None) else None,
        revenue=float(latest_actual.sales) if (latest_actual is not None and latest_actual.sales is not None) else None,
        fcf=fcf,
        eps_cagr_3y=eps_cagr_3y,
        sales_cagr_3y=sales_cagr_3y,
        fcf_yield=fcf_yield,
        per=per,
    )


__all__ = [
    "build_cf_scoring_input",
    "build_financial_metric_rows",
    "build_growth_phase",
    "build_per_level",
    "build_quarterly_metric_rows",
    "build_roic_level",
    "resolve_cf_scoring_as_of",
    "resolve_fiscal_end_month_from_forecast_pair",
]

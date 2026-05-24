"""Domain builder for Kabutan forecast output section."""

from __future__ import annotations

from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.models.financial_snapshot import FinancialMetricInputRow
from app.domain.policies.growth_metrics import (
    calc_eps_growth_rate,
    calc_operating_growth_rate,
    calc_cagr,
)
from app.domain.policies.growth_rows import build_growth_rows
from app.domain.policies.financial_metrics import calc_pbr, calc_roe, calc_roic_approx


def _fmt_oku(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value / 100:,.1f}億"


def _fmt_million_yen(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,}"


def _fmt_yen(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.1f}円"


def _fmt_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def calc_operating_margin(sales: int | None, operating_profit: int | None) -> float | None:
    if sales is None or operating_profit is None or sales == 0:
        return None
    return (operating_profit / sales) * 100


def calc_ordinary_margin(sales: int | None, ordinary_profit: int | None) -> float | None:
    if sales is None or ordinary_profit is None or sales == 0:
        return None
    return (ordinary_profit / sales) * 100


def build_profit_with_margin_text(profit: int | None, margin: float | None) -> str:
    return f"{_fmt_oku(profit)}({_fmt_percent(margin)})"


def _build_kabutan_row_line(row: KabutanForecastRow) -> str:
    year_label = f"{row.year}年(予)" if row.section == "予想" else f"{row.year}年"
    operating_margin = calc_operating_margin(row.sales, row.operating_profit)
    ordinary_margin = calc_ordinary_margin(row.sales, row.ordinary_profit)
    return (
        f"{year_label:<10}"
        f"{_fmt_oku(row.sales):>10}"
        f"{build_profit_with_margin_text(row.operating_profit, operating_margin):>20}"
        f"{build_profit_with_margin_text(row.ordinary_profit, ordinary_margin):>20}"
        f"{_fmt_oku(row.final_profit):>10}"
        f"{_fmt_yen(row.revised_eps):>10}"
        f"{_fmt_yen(row.dividend):>10}"
    )


def _build_kabutan_source_label(source: str, message: str | None) -> str:
    source_label = {"html": "HTML", "none": "取得不可"}.get(source, "取得不可")
    return f"株探ソース: {source_label}" if not message else f"株探ソース: {source_label} ({message})"


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


def _build_cashflow_lines(rows: list[KabutanForecastRow], cashflow_rows: tuple[KabutanCashflowRow, ...], market_cap: float | None) -> list[str]:
    selected_cashflow_rows = _preferred_cashflow_rows(cashflow_rows, max_years=3)
    if not selected_cashflow_rows:
        return ["■キャッシュフロー", "N/A"]

    forecast_by_year = _preferred_forecast_row_by_year(rows)

    lines = [
        "■キャッシュフロー",
        "[A] CF実績（百万円）",
        "年度 | フリーCF | 営業CF | 投資CF | 財務CF | 現金等残高",
    ]

    for cf_row in selected_cashflow_rows:
        lines.append(
            f"{cf_row.year} | {_fmt_million_yen(cf_row.free_cf)} | {_fmt_million_yen(cf_row.operating_cf)} | {_fmt_million_yen(cf_row.investing_cf)} | {_fmt_million_yen(cf_row.financing_cf)} | {_fmt_million_yen(cf_row.cash_stock)}"
        )

    lines.extend([
        "",
        "[B] 指標（%）",
        "年度 | 営業CFマージン | Cash conversion | FCFマージン | FCF Yield",
    ])

    for cf_row in selected_cashflow_rows:
        forecast_row = forecast_by_year.get(cf_row.year)
        sales = forecast_row.sales if forecast_row else None
        final_profit = forecast_row.final_profit if forecast_row else None
        operating_cf_margin = _safe_div(cf_row.operating_cf, sales)
        cash_conversion = _safe_div(cf_row.operating_cf, final_profit)
        resolved_fcf = _resolve_fcf_million_yen(cf_row)
        fcf_margin = _safe_div(resolved_fcf, sales)
        fcf_yield_pct = _calc_fcf_yield_pct(resolved_fcf, market_cap)

        lines.append(
            f"{cf_row.year} | {_fmt_percent(operating_cf_margin * 100 if operating_cf_margin is not None else None)} | {_fmt_percent(cash_conversion * 100 if cash_conversion is not None else None)} | {_fmt_percent(fcf_margin * 100 if fcf_margin is not None else None)} | {_fmt_percent(fcf_yield_pct)}"
        )

    return lines




def _fmt_multiplier(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}倍"


def _build_financial_lines(financial_metric_rows: tuple[FinancialMetricInputRow, ...]) -> list[str]:
    if not financial_metric_rows:
        return ["■財務ブロック", "　　　ROE(%)|ROIC(%)|PBR|", "N/A"]

    lines = ["■財務ブロック", "　　　ROE(%)|ROIC(%)|PBR|"]
    for row in financial_metric_rows:
        roe = calc_roe(row.net_income, row.equity)
        roic = calc_roic_approx(row.operating_profit, row.equity, row.interest_bearing_debt)
        pbr = calc_pbr(row.price, row.bps)
        lines.append(f"{row.year}年　{_fmt_percent(roe)}|{_fmt_percent(roic)}|{_fmt_multiplier(pbr)}")
    return lines


def _build_growth_metric_line(title: str, growth_rows: list[KabutanForecastRow], values: list[float | None]) -> str:
    parts = [title]
    for row, value in zip(growth_rows, values):
        year_label = f"{row.year}年(予)" if row.section == "予想" else f"{row.year}年"
        parts.append(f"{year_label} {_fmt_percent(value)}")
    return "　".join(parts)


def _select_cagr_row_by_year(growth_rows: list[KabutanForecastRow]) -> dict[int, KabutanForecastRow]:
    return {row.year: row for row in growth_rows}


def _build_cagr_line(title: str, growth_rows: list[KabutanForecastRow], metric_getter) -> str:
    row_by_year = _select_cagr_row_by_year(growth_rows)
    if not row_by_year:
        return f"{title} N/A"

    end_year = max(row_by_year.keys())
    start_year = end_year - 3
    start_row = row_by_year.get(start_year)
    end_row = row_by_year.get(end_year)
    cagr = calc_cagr(
        metric_getter(start_row) if start_row else None,
        metric_getter(end_row) if end_row else None,
        years=3,
    )
    return f"{title} {start_year}→{end_year} {_fmt_percent(cagr)}"

def build_kabutan_forecast_output(
    base_output: str,
    kabutan_forecast_pair: KabutanForecastPair | None,
    kabutan_source: str,
    kabutan_source_message: str | None,
    kabutan_cashflow_rows: tuple[KabutanCashflowRow, ...] = (),
    market_cap: float | None = None,
    financial_metric_rows: tuple[FinancialMetricInputRow, ...] = (),
) -> str:
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

    header = "　　　　　　売上　営業益(営業利益率)　経常益(経常利益率)　最終益　1株益　1株配当"
    row_lines = [_build_kabutan_row_line(row) for row in rows] if rows else ["データーが取得できません"]

    growth_lines: list[str] = []
    if rows:
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

        growth_lines.extend(
            [
                "■成長性",
                _build_growth_metric_line("営業利益成長率", growth_rows, operating_growth_rates),
                _build_growth_metric_line("EPS成長率", growth_rows, eps_growth_rates),
                _build_cagr_line("3年営業利益CAGR", growth_rows, lambda row: row.operating_profit if row else None),
                _build_cagr_line("3年EPS CAGR", growth_rows, lambda row: row.revised_eps if row else None),
            ]
        )

    section = "\n".join(
        ["", "■株探 通期業績推移", _build_kabutan_source_label(kabutan_source, kabutan_source_message), header, *row_lines, *growth_lines, *_build_cashflow_lines(rows, kabutan_cashflow_rows, market_cap), *_build_financial_lines(financial_metric_rows)]
    )
    return f"{base_output}\n{section}"


__all__ = ["build_kabutan_forecast_output"]

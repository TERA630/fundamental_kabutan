"""Domain builder for Kabutan forecast output section."""

from __future__ import annotations

from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.policies.growth_metrics import (
    calc_eps_growth_acceleration,
    calc_eps_growth_rate,
    calc_operating_growth_rate,
)
from app.domain.policies.growth_rows import build_growth_rows


def _fmt_oku(value: int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value / 100:,.1f}億"


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



def _build_kabutan_na_row_line(label: str) -> str:
    return f"{label:<10}{'N/A':>10}{'N/A':>20}{'N/A':>20}{'N/A':>10}{'N/A':>10}{'N/A':>10}"


def _build_kabutan_source_label(source: str, message: str | None) -> str:
    source_label = {"html": "HTML", "none": "取得不可"}.get(source, "取得不可")
    return f"株探ソース: {source_label}" if not message else f"株探ソース: {source_label} ({message})"


def build_kabutan_forecast_output(
    base_output: str,
    kabutan_forecast_pair: KabutanForecastPair | None,
    kabutan_source: str,
    kabutan_source_message: str | None,
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
        eps_accelerations: list[float | None] = []

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

        for index, eps_growth in enumerate(eps_growth_rates):
            previous_eps_growth = eps_growth_rates[index - 1] if index > 0 else None
            eps_accelerations.append(calc_eps_growth_acceleration(previous_eps_growth, eps_growth))

        def _build_growth_metric_line(title: str, values: list[float | None]) -> str:
            parts = [title]
            for row, value in zip(growth_rows, values):
                year_label = f"{row.year}年(予)" if row.section == "予想" else f"{row.year}年"
                parts.append(f"{year_label} {_fmt_percent(value)}")
            return "　".join(parts)

        growth_lines.extend(
            [
                "■成長性",
                _build_growth_metric_line("営業利益成長率", operating_growth_rates),
                _build_growth_metric_line("EPS成長率", eps_growth_rates),
                _build_growth_metric_line("EPS成長加速率", eps_accelerations),
            ]
        )

    section = "\n".join(
        ["", "■株探 通期業績推移", _build_kabutan_source_label(kabutan_source, kabutan_source_message), header, *row_lines, *growth_lines]
    )
    return f"{base_output}\n{section}"


__all__ = ["build_kabutan_forecast_output"]

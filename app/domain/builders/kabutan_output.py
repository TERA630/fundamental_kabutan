"""Domain builder for Kabutan forecast output section."""

from __future__ import annotations

from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow


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


def calc_operating_growth_rate(previous_operating_profit: int | None, current_operating_profit: int | None) -> float | None:
    if previous_operating_profit is None or current_operating_profit is None or previous_operating_profit == 0:
        return None
    return ((current_operating_profit - previous_operating_profit) / previous_operating_profit) * 100


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


def _build_kabutan_chain_row(metric_label: str, rows: list[KabutanForecastRow], attr: str) -> str:
    parts: list[str] = []
    for row in rows:
        value = getattr(row, attr)
        if attr in {"revised_eps", "dividend"}:
            metric_text = "N/A" if value is None else f"{value:,.1f}"
            suffix = "円"
        else:
            metric_text = _fmt_oku(value)
            suffix = ""
        year_label = f"予想 {row.year}" if row.section == "予想" else f"実績 {row.year}"
        parts.append(f"{year_label} {metric_text}{suffix}[KBT]")
    return f"{metric_label}：" + " -> ".join(parts)


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
        rows = [
            row
            for row in (
                kabutan_forecast_pair.previous2_actual,
                kabutan_forecast_pair.previous_actual,
                kabutan_forecast_pair.current_forecast,
                kabutan_forecast_pair.next_forecast,
            )
            if row is not None
        ]

    header = "　　　　　　売上　営業益(営業利益率)　経常益(経常利益率)　最終益　1株益　1株配当"
    row_lines = (
        [_build_kabutan_row_line(row) for row in rows]
        if rows
        else [
            _build_kabutan_na_row_line("実績(N/A)"),
            _build_kabutan_na_row_line("実績(N/A)"),
            _build_kabutan_na_row_line("今期予想(N/A)"),
            _build_kabutan_na_row_line("来期予想(N/A)"),
        ]
    )

    growth_lines: list[str] = []
    if rows:
        growth_lines.append("　　　　　　前年度営業利益成長率(%)")
        for index, row in enumerate(rows):
            previous_row = rows[index - 1] if index > 0 else None
            growth_rate = calc_operating_growth_rate(
                previous_row.operating_profit if previous_row else None,
                row.operating_profit,
            )
            year_label = f"{row.year}年(予)" if row.section == "予想" else f"{row.year}年"
            growth_lines.append(f"{year_label:<10}{_fmt_percent(growth_rate):>10}")

    chain_lines: list[str] = []
    if rows:
        chain_lines = [
            "",
            "■予想チェーン（通期） [ソース: 株探]",
            _build_kabutan_chain_row("売上", rows, "sales"),
            _build_kabutan_chain_row("営業益", rows, "operating_profit"),
            _build_kabutan_chain_row("最終益", rows, "final_profit"),
            _build_kabutan_chain_row("修正1株益", rows, "revised_eps"),
            _build_kabutan_chain_row("配当", rows, "dividend"),
        ]

    section = "\n".join(
        ["", "■株探 業績推移（通期）", _build_kabutan_source_label(kabutan_source, kabutan_source_message), header, *row_lines, *growth_lines, *chain_lines]
    )
    return f"{base_output}\n{section}"


__all__ = ["build_kabutan_forecast_output"]

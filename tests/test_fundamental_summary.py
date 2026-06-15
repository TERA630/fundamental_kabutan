from pathlib import Path

import pytest

from app.domain.builders.fundamental_summary import build_fundamental_summary_markdown
from app.domain.models.fundamental_summary import FundamentalSummaryRow, FundamentalSummaryTable
from app.domain.models.kabutan_balance_sheet import KabutanBalanceSheetRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService, KabutanFetchResult
from app.domain.usecases.fundamental_summary import FundamentalSummaryService


class FakeFundamentalAnalysisService:
    def __init__(self, fetch_results):
        self.fetch_results = fetch_results

    def fetch_price_snapshot(self, code4):
        return {
            "price": 1000.0,
            "market_cap": 2_000_000_000.0,
            "per": 99.0,
            "pbr": None,
            "industry": None,
            "div_yield": None,
            "payout_ratio": None,
            "as_of": None,
        }

    def fetch_kabutan_forecast_pair(self, code4, html_dir=None):
        return self.fetch_results[code4]

    def build_financial_metric_rows(self, *, price, forecast_pair, balance_sheet_rows):
        return FundamentalAnalysisService.build_financial_metric_rows(
            price=price,
            forecast_pair=forecast_pair,
            balance_sheet_rows=balance_sheet_rows,
        )

    def build_cf_scoring_input(self, **kwargs):
        return FundamentalAnalysisService.build_cf_scoring_input(**kwargs)

    def resolve_cf_scoring_as_of(self, **kwargs):
        return FundamentalAnalysisService.resolve_cf_scoring_as_of(**kwargs)


def _forecast_pair() -> KabutanForecastPair:
    rows = (
        KabutanForecastRow("2023.03", 2023, 3, "実績", 700, 90, 80, 70, 70.0, 8.0),
        KabutanForecastRow("2024.03", 2024, 3, "実績", 800, 120, 110, 90, 80.0, 10.0),
        KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 200, 180, 100, 100.0, 12.0),
        KabutanForecastRow("2026.03", 2026, 3, "予想", 1200, 300, 280, 150, 125.0, 14.0),
    )
    return KabutanForecastPair(
        previous2_actual=rows[0],
        previous_actual=rows[1],
        current_actual=rows[2],
        current_forecast=rows[3],
        next_forecast=None,
        all_rows=rows,
    )


def _fetch_result(pair):
    return KabutanFetchResult(
        pair=pair,
        source="html",
        cashflow_rows=(KabutanCashflowRow("2025.03", 2025, 3, 100, 250, -150, 0, 500),),
        balance_sheet_rows=(
            KabutanBalanceSheetRow("2025.03", 2025, 3, 500.0, 60.0, 2000, 800, 300, 0.25),
        ),
    )


def test_build_summary_table_sorts_and_builds_metrics():
    high_pair = _forecast_pair()
    low_pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=None,
        current_actual=None,
        current_forecast=KabutanForecastRow("2026.03", 2026, 3, "予想", None, None, None, None, None, None),
        next_forecast=None,
        all_rows=(KabutanForecastRow("2026.03", 2026, 3, "予想", None, None, None, None, None, None),),
    )
    service = FundamentalSummaryService(
        FakeFundamentalAnalysisService(
            {
                "1111": _fetch_result(high_pair),
                "2222": KabutanFetchResult(pair=low_pair, source="html"),
            }
        )
    )

    table = service.build_summary_table((("Low", "2222"), ("High", "1111")), kabutan_html_dir=Path("html"))

    assert [row.code4 for row in table.rows] == ["1111", "2222"]
    assert table.rows[0].total_score > table.rows[1].total_score
    assert table.rows[0].operating_margin == 25.0
    assert table.rows[0].operating_profit_cagr_3y == pytest.approx(49.38, abs=0.01)
    assert table.rows[0].roic == pytest.approx(14.0)
    assert table.rows[0].cash_conversion == 2.5
    assert table.rows[0].per == 8.0
    assert table.rows[0].investment_rate == -60.0
    assert table.rows[1].quality_score is None


def test_build_summary_table_skips_when_total_score_cannot_be_created():
    service = FundamentalSummaryService(
        FakeFundamentalAnalysisService(
            {
                "9999": KabutanFetchResult(pair=None, source="none", message="HTMLフォルダ未設定"),
            }
        )
    )

    table = service.build_summary_table((("Missing", "9999"),))

    assert table.rows == ()
    assert table.skipped[0].code4 == "9999"
    assert table.skipped[0].reason == "総合スコア作成不可"


def test_build_fundamental_summary_markdown_formats_na_values():
    table = FundamentalSummaryTable(
        rows=(
            FundamentalSummaryRow(
                name="Sample",
                code4="1234",
                total_score=50,
                quality_score=None,
                growth_score=10,
                valuation_score=5,
                operating_margin=12.345,
                operating_profit_cagr_3y=None,
                roic=None,
                cash_conversion=None,
                per=20.0,
                investment_rate=-60.0,
            ),
        )
    )

    markdown = build_fundamental_summary_markdown(table)

    assert "|Sample (1234)|50|N/A|10|5|12.3%|N/A|N/A|N/A|20.0倍|-60.0%|" in markdown

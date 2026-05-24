from app.domain.models.kabutan_balance_sheet import KabutanBalanceSheetRow
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService


def _pair(rows: list[KabutanForecastRow]) -> KabutanForecastPair:
    return KabutanForecastPair(
        previous2_actual=rows[0],
        previous_actual=rows[1],
        current_actual=rows[2],
        current_forecast=rows[3],
        next_forecast=rows[4] if len(rows) > 4 else None,
        all_rows=tuple(rows),
    )


def test_build_financial_metric_rows_selects_latest_common_three_years():
    rows = [
        KabutanForecastRow("2022.03", 2022, 3, "実績", 1000, 100, 90, 80, 10.0, 2.0),
        KabutanForecastRow("2023.03", 2023, 3, "実績", 1000, 110, 90, 85, 10.0, 2.0),
        KabutanForecastRow("2024.03", 2024, 3, "実績", 1000, 120, 90, 90, 10.0, 2.0),
        KabutanForecastRow("2025.03", 2025, 3, "実績", 1000, 130, 90, 95, 10.0, 2.0),
        KabutanForecastRow("2026.03", 2026, 3, "予想", 1000, 140, 90, 100, 10.0, 2.0),
    ]
    bs = [
        KabutanBalanceSheetRow("2022.03", 2022, 3, 1000.0, 50.0, 1000, 300, 200, 0.2),
        KabutanBalanceSheetRow("2023.03", 2023, 3, 1100.0, 50.0, 1000, 320, 200, 0.25),
        KabutanBalanceSheetRow("2024.03", 2024, 3, 1200.0, 50.0, 1000, 340, 200, 0.3),
        KabutanBalanceSheetRow("2025.03", 2025, 3, None, 50.0, 1000, 360, 200, 0.35),
    ]

    out = FundamentalAnalysisService.build_financial_metric_rows(price=2500.0, forecast_pair=_pair(rows), balance_sheet_rows=tuple(bs))

    assert [x.year for x in out] == [2022, 2023, 2024]
    assert out[-1].interest_bearing_debt == 102
    assert out[-1].price == 2500.0


def test_build_financial_metric_rows_returns_empty_when_missing_inputs():
    out = FundamentalAnalysisService.build_financial_metric_rows(price=2500.0, forecast_pair=None, balance_sheet_rows=())
    assert out == ()

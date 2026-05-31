from pathlib import Path

from app.domain.models.analyst_estimates import AnalystEstimates
from app.domain.models.kabutan_balance_sheet import KabutanBalanceSheetRow
from app.domain.models.kabutan_cashflow import KabutanCashflowRow
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService, KabutanFetchResult
from app.presenters import build_fundamental_output


class DummyCache:
    def get(self, _key, _ttl):
        return None

    def set(self, _key, _value):
        return None


class ServiceForTest(FundamentalAnalysisService):
    def __init__(self, fetch_result: KabutanFetchResult):
        super().__init__(file_cache=DummyCache(), fetch_market_snapshot=lambda _code: {})
        self._fetch_result = fetch_result

    def fetch_price_snapshot(self, _code4: str):
        return {"price": 1000.0, "market_cap": 100_000_000_000.0, "per": 20.0, "pbr": None, "industry": None, "div_yield": None, "payout_ratio": None}

    def fetch_kabutan_forecast_pair(self, code4: str, html_dir: Path | None = None, allow_kabutan_web_fallback: bool = False):
        return self._fetch_result


def _pair_with_actual_rows() -> KabutanForecastPair:
    rows = (
        KabutanForecastRow("2022.03", 2022, 3, "実績", 7000, 700, 650, 500, 50.0, 10.0),
        KabutanForecastRow("2023.03", 2023, 3, "実績", 8000, 800, 750, 600, 70.0, 12.0),
        KabutanForecastRow("2024.03", 2024, 3, "実績", 9000, 1000, 900, 700, 90.0, 14.0),
        KabutanForecastRow("2025.03", 2025, 3, "実績", 10000, 1200, 1100, 800, 120.0, 16.0),
        KabutanForecastRow("2026.03", 2026, 3, "予想", 12000, 1500, 1300, 900, 130.0, 18.0),
    )
    return KabutanForecastPair(
        previous2_actual=rows[1],
        previous_actual=rows[2],
        current_actual=rows[3],
        current_forecast=rows[4],
        next_forecast=None,
        all_rows=rows,
    )


def test_build_analysis_output_passes_cf_scoring_result_to_builder():
    pair = _pair_with_actual_rows()
    fetch_result = KabutanFetchResult(
        pair=pair,
        source="html",
        cashflow_rows=(KabutanCashflowRow("2025.03", 2025, 3, 600, 1000, -400, -100, 300),),
        balance_sheet_rows=(KabutanBalanceSheetRow("2025.03", 2025, 3, 1500.0, None, None, 4000, None, 0.5),),
    )
    service = ServiceForTest(fetch_result)

    captured = {}

    def build_output_fn(**kwargs):
        captured.update(kwargs)
        return "ok"

    out = service.build_analysis_output("Test", "1234", build_output_fn)

    assert out == "ok"
    assert "cf_scoring_result" in captured
    assert captured["cf_scoring_result"] is not None
    assert captured["cf_scoring_result"].total.max_points == 100
    assert captured["cf_scoring_result"].as_of == "2025-03"
    assert captured["growth_phase"] is not None
    assert captured["per_level"] == "割安PER"
    assert captured["roic_level"] == "高ROIC"
    assert isinstance(captured["analyst_estimates"], AnalystEstimates)


def test_build_analysis_output_keeps_running_with_none_cf_score_when_data_missing():
    fetch_result = KabutanFetchResult(pair=None, source="none")
    service = ServiceForTest(fetch_result)

    captured = {}

    def build_output_fn(**kwargs):
        captured.update(kwargs)
        return "ok"

    out = service.build_analysis_output("Test", "1234", build_output_fn)

    assert out == "ok"
    assert "cf_scoring_result" in captured
    assert captured["cf_scoring_result"] is None
    assert captured["growth_phase"] is None
    assert captured["per_level"] is None
    assert captured["roic_level"] is None



def test_build_analysis_output_reflects_opening_summary_labels_in_display():
    pair = _pair_with_actual_rows()
    fetch_result = KabutanFetchResult(
        pair=pair,
        source="html",
        cashflow_rows=(KabutanCashflowRow("2025.03", 2025, 3, 600, 1000, -400, -100, 300),),
        balance_sheet_rows=(KabutanBalanceSheetRow("2025.03", 2025, 3, 1500.0, None, None, 4000, None, 0.5),),
    )
    service = ServiceForTest(fetch_result)

    out = service.build_analysis_output("Test", "1234", build_fundamental_output)

    assert "【Test (1234)】" in out
    assert "総合評価" in out
    assert "割安PER" in out
    assert "高ROIC" in out
    assert "投資分類：" not in out
    assert "算出基準：" not in out

def test_resolve_cf_scoring_as_of_falls_back_to_latest_observed_minus_one_when_actual_missing():
    rows = (
        KabutanForecastRow("2026.03", 2026, 3, "予想", 10000, 1200, 1100, 800, 120.0, 16.0),
        KabutanForecastRow("2027.03", 2027, 3, "予想", 12000, 1500, 1300, 900, 130.0, 18.0),
    )
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=None,
        current_actual=None,
        current_forecast=rows[0],
        next_forecast=rows[1],
        all_rows=rows,
    )
    as_of = FundamentalAnalysisService.resolve_cf_scoring_as_of(
        price_snapshot={"price": 1000.0, "as_of": "2026-05-27"},
        forecast_pair=pair,
    )
    assert as_of == "2026-03"


def test_resolve_cf_scoring_as_of_prefers_latest_actual_over_snapshot_as_of():
    rows = (
        KabutanForecastRow("2024.03", 2024, 3, "実績", 8000, 900, 800, 700, 90.0, 14.0),
        KabutanForecastRow("2025.03", 2025, 3, "実績", 10000, 1200, 1100, 800, 120.0, 16.0),
        KabutanForecastRow("2026.03", 2026, 3, "予想", 12000, 1500, 1300, 900, 130.0, 18.0),
    )
    pair = KabutanForecastPair(
        previous2_actual=rows[0],
        previous_actual=rows[1],
        current_actual=rows[1],
        current_forecast=rows[2],
        next_forecast=None,
        all_rows=rows,
    )
    as_of = FundamentalAnalysisService.resolve_cf_scoring_as_of(
        price_snapshot={"price": 1000.0, "as_of": "2026-12-31"},
        forecast_pair=pair,
    )
    assert as_of == "2025-03"

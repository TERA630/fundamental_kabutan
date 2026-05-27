import unittest
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow
from app.domain.models.quarterly_financials import QuarterlyActual


class InMemoryCache:
    def __init__(self):
        self.store = {}

    def get(self, key, _ttl):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def get_or_fetch(self, key, _ttl, fetcher):
        if key in self.store:
            return self.store[key]
        value = fetcher()
        self.store[key] = value
        return value


class FakeMarketProvider:
    def __init__(self):
        self.calls = 0

    def __call__(self, _code4):
        self.calls += 1
        return {"price": 2000.0, "market_cap": 123_000_000_000.0}


class TestFundamentalAnalysisService(unittest.TestCase):
    def test_fetch_uses_injected_dependencies_and_cache(self):
        market = FakeMarketProvider()
        cache = InMemoryCache()
        service = FundamentalAnalysisService(
            file_cache=cache,
            fetch_market_snapshot=market,
        )

        snap1 = service.fetch_price_snapshot("8058")
        snap2 = service.fetch_price_snapshot("8058")

        self.assertEqual(snap1, snap2)
        self.assertEqual(market.calls, 1)

    def test_price_none_is_not_cached(self):
        cache = InMemoryCache()

        class EmptyPriceProvider:
            def __init__(self):
                self.calls = 0

            def __call__(self, _code4):
                self.calls += 1
                return {"price": None, "market_cap": None}

        market = EmptyPriceProvider()
        service = FundamentalAnalysisService(
            file_cache=cache,
            fetch_market_snapshot=market,
        )

        snap1 = service.fetch_price_snapshot("5803")
        snap2 = service.fetch_price_snapshot("5803")

        expected = {"price": None, "market_cap": None, "per": None, "pbr": None, "industry": None, "div_yield": None, "payout_ratio": None}
        self.assertEqual(snap1, expected)
        self.assertEqual(snap2, expected)
        self.assertEqual(market.calls, 2)

    def test_fetch_kabutan_forecast_pair_returns_none_when_html_dir_is_none(self):
        class FakeKabutanUseCase:
            def __init__(self):
                self.repository = object()

        service = FundamentalAnalysisService(
            file_cache=InMemoryCache(),
            fetch_market_snapshot=FakeMarketProvider(),
            fetch_kabutan_forecast_usecase=FakeKabutanUseCase(),
        )

        result = service.fetch_kabutan_forecast_pair("8058", html_dir=None)

        self.assertEqual(result.source, "none")
        self.assertEqual(result.message, "HTMLフォルダ未設定")
        self.assertIsNone(result.pair)


if __name__ == "__main__":
    unittest.main()


def test_build_quarterly_metric_rows_prefers_fiscal_end_month_from_forecast_pair():
    rows = (
        QuarterlyActual("1234", 2025, None, 12, 100, 10, 10, 8, 1.0, None),
        QuarterlyActual("1234", 2026, None, 12, 150, 15, 15, 12, 1.5, None),
    )
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2025.06", 2025, 6, "実績", 1000, 100, 90, 80),
        current_actual=None,
        current_forecast=KabutanForecastRow("2026.06", 2026, 6, "予想", 1200, 120, 100, 90),
        next_forecast=None,
        all_rows=(
            KabutanForecastRow("2025.06", 2025, 6, "実績", 1000, 100, 90, 80),
            KabutanForecastRow("2026.06", 2026, 6, "予想", 1200, 120, 100, 90),
        ),
    )
    out = FundamentalAnalysisService.build_quarterly_metric_rows(code4="1234", rows=rows, forecast_pair=pair)
    assert len(out) == 2
    assert out[0].quarter.value == "Q2"


def test_build_quarterly_metric_rows_falls_back_to_quarter_rows_when_forecast_pair_missing():
    rows = (
        QuarterlyActual("1234", 2025, None, 12, 100, 10, 10, 8, 1.0, None),
        QuarterlyActual("1234", 2026, None, 12, 150, 15, 15, 12, 1.5, None),
    )
    out = FundamentalAnalysisService.build_quarterly_metric_rows(code4="1234", rows=rows, forecast_pair=None)
    assert len(out) == 2
    assert out[0].quarter.value == "Q4"


def test_build_quarterly_metric_rows_returns_empty_when_rows_missing():
    out = FundamentalAnalysisService.build_quarterly_metric_rows(code4="1234", rows=(), forecast_pair=None)
    assert out == ()



def test_build_cf_scoring_input_prefers_next_forecast_eps_for_per():
    pair = KabutanForecastPair(
        previous2_actual=None,
        previous_actual=KabutanForecastRow("2024.03", 2024, 3, "実績", 1000, 100, 90, 80, 100.0, None),
        current_actual=KabutanForecastRow("2025.03", 2025, 3, "実績", 1200, 120, 100, 90, 110.0, None),
        current_forecast=KabutanForecastRow("2026.03", 2026, 3, "予想", 1300, 130, 110, 95, 130.0, None),
        next_forecast=KabutanForecastRow("2027.03", 2027, 3, "予想", 1400, 150, 120, 100, 200.0, None),
        all_rows=(
            KabutanForecastRow("2024.03", 2024, 3, "実績", 1000, 100, 90, 80, 100.0, None),
            KabutanForecastRow("2025.03", 2025, 3, "実績", 1200, 120, 100, 90, 110.0, None),
        ),
    )
    from app.domain.models.kabutan_cashflow import KabutanCashflowRow
    from app.domain.models.financial_snapshot import FinancialMetricInputRow

    scoring_input = FundamentalAnalysisService.build_cf_scoring_input(
        code4="1234",
        as_of=None,
        price=2000.0,
        market_per=99.0,
        forecast_pair=pair,
        cashflow_rows=(KabutanCashflowRow("2025.03", 2025, 3, 50, 100, -50, 0, 0),),
        financial_metric_rows=(FinancialMetricInputRow(2025, 90, 600, 120, 100, 1000.0, 2000.0),),
    )
    assert scoring_input is not None
    assert scoring_input.per == 10.0

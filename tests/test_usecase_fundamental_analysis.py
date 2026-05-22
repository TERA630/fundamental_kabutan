import unittest
from app.domain.usecases.fundamental_analysis import FundamentalAnalysisService


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

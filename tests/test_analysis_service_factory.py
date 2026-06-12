from app.data.file_cache import FileCache
from app.domain.models.market_data import MarketDataBundle, MarketSnapshot
from app.services import analysis_service_factory as factory


def test_build_default_fundamental_service_with_market_bundle_reuses_snapshot(tmp_path, monkeypatch):
    calls = {"fallback": 0}

    monkeypatch.setattr(
        factory,
        "fetch_yfinance_snapshot",
        lambda _code4: calls.__setitem__("fallback", calls["fallback"] + 1) or {"price": 999.0},
    )
    bundle = MarketDataBundle(
        code4="7203",
        daily_history=None,
        intraday_history=None,
        snapshot=MarketSnapshot(price=123.0),
    )

    service = factory.build_default_fundamental_service_with_market_bundle(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        bundle=bundle,
    )

    assert service.fetch_market_snapshot("7203")["price"] == 123.0
    assert service.fetch_market_snapshot("7974")["price"] == 999.0
    assert calls["fallback"] == 1


def test_build_default_market_and_technical_services_require_no_manual_providers(tmp_path):
    file_cache = FileCache(base_dir=tmp_path / "cache")

    market_service = factory.build_default_market_data_service(file_cache)
    technical_service = factory.build_default_technical_service(file_cache)

    assert market_service.file_cache is file_cache
    assert technical_service.file_cache is file_cache

import pandas as pd

from app.domain.models.market_data import MARKET_SNAPSHOT_KEYS, MarketDataBundle, MarketSnapshot
from app.domain.usecases.fundamental_analysis import normalize_market_snapshot


def test_market_snapshot_round_trips_to_legacy_dict_shape():
    snapshot = MarketSnapshot(price=1000.0, market_cap=10_000.0, industry="機械")

    payload = snapshot.to_dict()

    assert tuple(payload.keys()) == MARKET_SNAPSHOT_KEYS
    assert payload["price"] == 1000.0
    assert payload["market_cap"] == 10_000.0
    assert payload["industry"] == "機械"
    assert payload["as_of"] is None


def test_normalize_market_snapshot_accepts_typed_snapshot():
    normalized = normalize_market_snapshot(MarketSnapshot(price=2000.0, per=15.5))

    assert normalized["price"] == 2000.0
    assert normalized["per"] == 15.5
    assert normalized["pbr"] is None


def test_market_data_bundle_groups_histories_and_snapshot():
    daily = pd.DataFrame({"Close": [100.0]})
    intraday = pd.DataFrame({"Close": [101.0]})
    snapshot = MarketSnapshot(price=100.0)

    bundle = MarketDataBundle(
        code4="7203",
        daily_history=daily,
        intraday_history=intraday,
        snapshot=snapshot,
    )

    assert bundle.code4 == "7203"
    assert bundle.daily_history.iloc[-1]["Close"] == 100.0
    assert bundle.intraday_history.iloc[-1]["Close"] == 101.0
    assert bundle.snapshot.has_price

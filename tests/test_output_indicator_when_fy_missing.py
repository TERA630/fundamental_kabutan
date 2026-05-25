from app.domain.builders.fundamental_output import build_fundamental_output_text
from app.domain.models.kabutan_forecast import KabutanForecastPair, KabutanForecastRow

def test_build_output_shows_indicator_when_fy_missing():
    text = build_fundamental_output_text(
        name='住友', code4='5802', master=None, price=4850.0, market_cap=8_029_950_000_000.0,
        market_snapshot={
            'price':4850.0,'market_cap':8_029_950_000_000.0,'pbr':3.28,'industry':'非鉄金属','payout_ratio':30.30
        },
        kabutan_forecast_pair=KabutanForecastPair(
            previous2_actual=KabutanForecastRow("2025/03", 2025, 3, "実績", None, None, None, None, 200.0, 70.0),
            previous_actual=KabutanForecastRow("2026/03", 2026, 3, "実績", None, None, None, None, 220.0, 80.0),
            current_actual=None,
            current_forecast=KabutanForecastRow("2027/03", 2027, 3, "予想", None, None, None, None, 250.0, 90.0),
            next_forecast=None,
        ),
    )
    assert '■指標' in text
    assert '株価：4,850円 / PBR 3.28 / ROE N/A' in text
    assert '業種：非鉄金属' in text
    assert 'PER：2025/03(実績) 24.2倍／2026/03(実績) 22.0倍／2027/03(予) 19.4倍' in text
    assert '配当利回り：2025/03(実績) 1.44%／2026/03(実績) 1.65%／2027/03(予) 1.86%' in text
    assert '通期(FY)データを抽出できませんでした。' not in text


def test_build_output_keeps_per_when_dividend_missing():
    text = build_fundamental_output_text(
        name='無配株', code4='9999', master=None, price=1000.0, market_cap=1_000_000_000.0,
        market_snapshot={'pbr': 1.2, 'industry': 'サービス'},
        kabutan_forecast_pair=KabutanForecastPair(
            previous2_actual=KabutanForecastRow("2025/03", 2025, 3, "実績", None, None, None, None, 100.0, None),
            previous_actual=KabutanForecastRow("2026/03", 2026, 3, "実績", None, None, None, None, 125.0, None),
            current_actual=None,
            current_forecast=KabutanForecastRow("2027/03", 2027, 3, "予想", None, None, None, None, 200.0, None),
            next_forecast=None,
        ),
    )
    assert 'PER：2025/03(実績) 10.0倍／2026/03(実績) 8.0倍／2027/03(予) 5.0倍' in text
    assert '配当利回り：N/A' in text

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
    assert '■指標' not in text
    assert '株価：4,850円' in text
    assert '時価総額：80,299.5億円(大型主役)' in text
    assert '■バリュエーション' in text
    assert '年度|2025年(実績)|2026年(実績)|2027年(予)' in text
    assert 'PER|24.2倍|22.0倍|19.4倍' in text
    assert '配当利回り|1.44%|1.65%|1.86%' in text
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
    assert '年度|2025年(実績)|2026年(実績)|2027年(予)' in text
    assert 'PER|10.0倍|8.0倍|5.0倍' in text
    assert '配当利回り|N/A' in text


def test_build_output_uses_market_per_when_forecast_eps_missing():
    text = build_fundamental_output_text(
        name='EPS欠損', code4='8888', master=None, price=1000.0, market_cap=1_000_000_000.0,
        market_snapshot={'per': 18.6, 'industry': 'サービス'},
        kabutan_forecast_pair=KabutanForecastPair(
            previous2_actual=KabutanForecastRow("2025/03", 2025, 3, "実績", None, None, None, None, None, None),
            previous_actual=KabutanForecastRow("2026/03", 2026, 3, "実績", None, None, None, None, None, None),
            current_actual=None,
            current_forecast=KabutanForecastRow("2027/03", 2027, 3, "予想", None, None, None, None, None, None),
            next_forecast=None,
        ),
    )
    assert '年度|市場PER' in text
    assert 'PER|18.6倍' in text

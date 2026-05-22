from app.domain.builders.fundamental_output import build_fundamental_output_text

def test_build_output_shows_indicator_when_fy_missing():
    text = build_fundamental_output_text(
        name='住友', code4='5802', master=None, price=4850.0, market_cap=8_029_950_000_000.0,
        market_snapshot={
            'price':4850.0,'market_cap':8_029_950_000_000.0,'per':14.68,'pbr':3.28,'industry':'非鉄金属','div_yield':2.06,'payout_ratio':30.30
        }
    )
    assert '■指標' in text
    assert '株価：4,850円 / PBR 3.28 / ROE N/A' in text
    assert '業種：非鉄金属' in text
    assert 'PER：' in text
    assert '配当利回り：' in text
    assert '通期(FY)データを抽出できませんでした。' not in text

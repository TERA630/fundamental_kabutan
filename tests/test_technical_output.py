from dataclasses import replace
from types import SimpleNamespace

from app.domain.builders.technical_output import _build_resistance_lines, build_technical_output
from app.domain.usecases.technical_analysis import TechnicalAnalysisService
import pandas as pd


class InMemoryCache:
    def __init__(self):
        self.store = {}

    def get(self, key, ttl_sec):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value


def _daily_history(rows: int = 70) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="B")
    close = pd.Series([100 + i for i in range(rows)], index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": close - 1,
            "High": close + 2,
            "Low": close - 3,
            "Close": close,
            "Volume": [1000 + i for i in range(rows)],
        },
        index=index,
    )


def _intraday_history() -> pd.DataFrame:
    prev_date = _daily_history().index[-2].date().isoformat()
    index = pd.to_datetime(
        [
            f"{prev_date} 09:00",
            f"{prev_date} 11:25",
            f"{prev_date} 12:30",
            f"{prev_date} 14:55",
        ]
    )
    return pd.DataFrame(
        {
            "Open": [166.0, 167.0, 167.0, 168.0],
            "High": [168.0, 169.0, 168.0, 169.0],
            "Low": [165.0, 166.0, 166.0, 167.0],
            "Close": [167.0, 168.0, 168.0, 168.0],
            "Volume": [1000.0, 1000.0, 1000.0, 2000.0],
        },
        index=index,
    )


def test_build_technical_output_contains_summary_and_sections():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    output = build_technical_output(result)

    assert output.startswith("取得時刻：2026-04-08 終値\n【銘柄】Sample (1234)")
    assert "株価：" in output
    assert "終端位置" in output
    assert "取得時刻：2026-04-08 終値" in output
    assert "位置：25日線" in output
    assert "傾き：" not in output
    assert "VWAP" in output
    assert "Vmap" not in output
    assert "需給（VWAP）：当日前場／後場　◯／◯　前日前場／後場　◯／◯" in output
    assert "出来高比　101%(前日比+0.1%)" in output
    assert "60日レンジ　98.4% |" in output
    assert "下値目安：165(preL)→157(25ME)→146(20dL)" in output
    assert "\n　支持：" not in output
    assert "抵抗：170(preH/20dH/60dH)" in output
    assert "短評：B2 過熱極大｜新規買い非推奨。利確優先。｜短期監視のみ。追加買い不可。" in output
    assert "崩れ警戒：低（1点）" in output
    assert "崩れ警戒スコア：" not in output
    assert "底打ち初動判定：" not in output
    assert "ホールド判定：○" in output
    assert "戦略判定：\n前場深押し×：深押しに見えても崩れ初動の可能性が高い。" in output
    assert "前場VWAP回復×：VWAP回復だけでは新規不可。" in output
    assert "後場VWAP回復×：新規不可。保有中なら利確・逆指値管理を優先。" in output
    assert output.index("短評：B2 過熱極大") < output.index("■モメンタム")
    assert output.index("崩れ警戒：低（1点）") < output.index("■モメンタム")
    assert output.index("ホールド判定：○") < output.index("戦略判定：") < output.index("■モメンタム")
    assert "■モメンタム" in output
    assert "3日高値更新：〇〇〇" in output
    assert "3日安値切り上げ：〇〇〇" in output
    assert "3日騰落率　+1.2%" in output
    assert "3日出来高　101%→101%→101%" in output
    assert "■当日位置・レンジ" in output
    assert "O 168.00　H 171.00　L 166.00　C 169.00" in output
    assert "\n始値：" not in output
    assert "\n高値：" not in output
    assert "\n安値：" not in output
    assert "\n終値：" not in output
    assert "■移動平均・Vwap" in output
    assert "前場Vwap：167.17" in output
    assert "後場Vwap：167.78" in output
    assert "■移動平均・出来高" not in output
    assert "出来高：1,069株" not in output
    assert "■抵抗線" not in output
    assert "■前日評価" in output
    assert "終値 168（VWAP +0.47円 / +0.3% / 0.09ATR）騰落率+0.6%" in output
    assert "前日Vwap(前・後場)" not in output
    assert "高値更新 〇 / 安値維持 〇" not in output
    assert "前日出来高：　20日平均比　100.9%(前々日比　+0.1%)" in output
    assert "後場評価 高値維持" in output
    assert "後場評価 高値維持 / VWAP上" not in output
    assert "前日レンジ 165-170（1.00ATR）　終位置 60.0%" in output
    assert "前日ローソク足型：　小陽線" in output
    assert "前日ローソク足型：　小陽線＋" not in output
    assert "■支持線" not in output
    assert "■節目・ブレイクライン" not in output
    assert "■流れ" not in output
    assert "トレンド：" not in output
    assert output.index("■移動平均・Vwap") < output.index("■前日評価")


def test_build_technical_output_marks_daily_reference_vwap():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _daily_history(0),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    output = build_technical_output(result)

    assert "VWAP" in output
    assert "Vmap" not in output
    assert "取得時刻：2026-04-08 終値" in output
    assert "(日足参考値)" in output
    assert "需給（VWAP）：当日 N/A　前日前場／後場　N/A／N/A" in output
    assert "\n前場Vwap：" not in output
    assert "\n後場Vwap：" not in output


def test_build_technical_output_marks_each_session_vwap_against_latest_price():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    result = replace(
        result,
        vwap_snapshot={
            **result.vwap_snapshot,
            "current_am_vwap": 170.0,
            "current_pm_vwap": 168.0,
        },
    )

    output = build_technical_output(result)

    assert "需給（VWAP）：当日前場／後場　×／◯　前日前場／後場　◯／◯" in output
    assert "前場Vwap：170.00" in output
    assert "後場Vwap：168.00" in output


def test_build_technical_output_omits_current_pm_mark_during_am_session():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    result = replace(
        result,
        vwap_snapshot={
            **result.vwap_snapshot,
            "current_intraday_session": "前場",
            "current_am_vwap": 170.0,
            "current_pm_vwap": None,
        },
    )

    output = build_technical_output(result)
    supply_line = next(line for line in output.splitlines() if "需給（VWAP）" in line)

    assert supply_line == "　需給（VWAP）：当日前場　×　前日前場／後場　◯／◯"
    assert "当日後場" not in supply_line


def test_build_technical_output_shows_bottoming_start_only_below_ma25():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    moving_average = replace(
        result.snapshot.moving_average,
        ma25=170.0,
        dev25_pct=-0.59,
        ma25_distance_atr=0.2,
    )
    result = replace(result, snapshot=replace(result.snapshot, moving_average=moving_average))
    result = replace(
        result,
        vwap_snapshot={**result.vwap_snapshot, "vwap_maintained_15m": True},
    )

    output = build_technical_output(result)

    assert "短評：D3強｜VWAP維持・出来高伴う｜小さく可。D3内で最有力" in output
    assert "詳細：" not in output
    assert "底打ち初動判定：成立" in output
    assert "ホールド判定：△" in output
    assert "戦略判定：\n前場深押し○：押し目待ちは" in output
    assert "前場VWAP回復◎：最有力。VWAP15分維持＋出来高80%以上で小さく可。" in output
    assert "後場VWAP回復◎：後場VWAP上維持なら持ち越し候補。" in output


def test_build_technical_output_uses_d1a_detail_headline_and_strategy():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    moving_average = replace(result.snapshot.moving_average, ma25=174.0)
    result = replace(result, snapshot=replace(result.snapshot, moving_average=moving_average))
    result = replace(
        result,
        vwap_snapshot={**result.vwap_snapshot, "vwap_maintained_15m": False},
    )

    output = build_technical_output(result)

    assert "短評：D1a 戻り途中・25日線接近｜監視優先。D3化なら小さく可" in output
    assert "前場深押し△：地合い良好なら" in output
    assert "前場VWAP回復△：VWAP回復だけでは不可。" in output


def test_build_technical_output_uses_d2_headline_and_recovery_stage():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    moving_average = replace(result.snapshot.moving_average, ma25=180.0)
    result = replace(result, snapshot=replace(result.snapshot, moving_average=moving_average))
    result = replace(result, vwap_snapshot={**result.vwap_snapshot, "vwap": 170.0})

    output = build_technical_output(result)

    assert "短評：D2 底打ち候補｜支持線反発待ち｜支持線反発候補。原則VWAP回復待ち" in output
    assert "前場VWAP回復△：VWAP15分維持なら試し玉候補" in output
    assert "D3化すれば○" in output


def test_build_technical_output_marks_previous_session_intraday_na_when_missing():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: pd.DataFrame(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    output = build_technical_output(result)

    assert "終値 168（VWAP N/A円 / N/A / N/A）騰落率+0.6%" in output
    assert "需給（VWAP）：当日 N/A　前日前場／後場　N/A／N/A" in output
    assert "前日Vwap(前・後場)" not in output
    assert "高値更新 〇 / 安値維持 〇" not in output
    assert "後場評価 N/A" in output
    assert "/ VWAPN/A" not in output


def test_build_resistance_lines_keeps_only_prices_above_latest_in_ascending_order():
    result = SimpleNamespace(
        snapshot=SimpleNamespace(
            price=SimpleNamespace(latest=100.0),
            previous_session=SimpleNamespace(prev_high=104.0),
            moving_average=SimpleNamespace(ma25=102.0),
            breakline=SimpleNamespace(recent20_high=98.0, recent60_high=106.0),
        )
    )

    lines = _build_resistance_lines(result)

    assert [(line.label, line.price) for line in lines] == [
        ("25日線", 102.0),
        ("前日高値", 104.0),
        ("60日高値", 106.0),
    ]


def test_opening_downside_targets_include_moving_averages_and_keep_three_nearest_levels():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    moving_average = replace(result.snapshot.moving_average, ma25=168.0, ma75=160.0)
    previous_session = replace(result.snapshot.previous_session, prev_low=165.0)
    breakline = replace(result.snapshot.breakline, recent20_low=160.0, recent60_low=150.0)
    result = replace(
        result,
        snapshot=replace(
            result.snapshot,
            moving_average=moving_average,
            previous_session=previous_session,
            breakline=breakline,
        ),
    )

    output = build_technical_output(result)

    assert "下値目安：168(25ME)→165(preL)→160(20dL/75ME)" in output
    assert "150(60dL)" not in output.split("\n　抵抗：", 1)[0]

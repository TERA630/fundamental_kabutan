from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace

from app.domain.builders.technical_output import _build_resistance_lines, build_technical_output
from app.domain.models.manual_technical_quote import ManualTechnicalQuote
from app.domain.models.rsi_analysis import RsiAnalysis, RsiDivergence, RsiSignal
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
    assert "VWAP+1.47円/0.29ATR" in output
    assert "VWAP+1.47円/+0.9%/0.29ATR" not in output
    assert "Vmap" not in output
    assert "需給（VWAP）：当日前場／後場　◯／◯　前日前場／後場　◯／◯" in output
    assert "出来高：20日平均比 101% / 前日比100%" in output
    assert "60日レンジ　98.4% |" in output
    assert "前場VWAP+1.1% 後場VWAP+0.7%" in output
    assert "リスクリターン：RR0.25" in output
    assert "下値：165(preL)：2.4%→157(25ME)：7.1%→146(20dL)：13.6%" in output
    assert "下値目安：" not in output
    assert "下値余地：" not in output
    assert "\n　支持：" not in output
    assert "抵抗：170(preH/20dH/60dH)：0.6%" in output
    assert "抵抗余地：" not in output
    assert "RSI：5分N/A / 時間N/A" in output
    assert "RSI総合：N/A" in output
    assert "短評：A1弱 上方乖離｜要確認｜中央値マイナス｜押し目確認｜" in output
    assert "｜5日線良好" in output
    assert "崩れ 1/5：候補｜買い条件は別確認" in output
    assert "底打ち初動判定：" not in output
    assert "ホールド判定：○" in output
    assert "戦略判定：\n前場VWAP回復○：" in output
    assert "前場深押し" not in output
    assert "前場VWAP回復○：VWAP回復＋15分以上維持なら小さく検討可。" in output
    assert "後場VWAP回復○：後場VWAP上維持ならエントリー候補。" in output
    assert output.index("短評：A1弱 上方乖離｜要確認｜中央値マイナス｜押し目確認｜") < output.index("■モメンタム")
    assert output.index("崩れ 1/5：候補｜買い条件は別確認") < output.index("■モメンタム")
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
    assert "■重要価格" in output
    assert "\n5日線：" not in output
    assert "25日線：157.00" in output
    assert "25日線：157.00（" not in output
    assert "前場Vwap：167.17" in output
    assert "後場Vwap：167.78" in output
    assert "■移動平均・出来高" not in output
    assert "出来高：1,069株" not in output
    assert "■抵抗線" not in output
    assert "■前日評価" in output
    assert "前日終値：168円（VWAP+0.47円／騰落率+0.6%）　終端位置：60.0%　小陽線（レンジ165－170）" in output
    assert "前日Vwap(前・後場)" not in output
    assert "高値更新 〇 / 安値維持 〇" not in output
    assert "前日出来高：20日平均比　100.9%" in output
    assert "前々日比" not in output
    assert "後場評価：" not in output
    assert "■支持線" not in output
    assert "■節目・ブレイクライン" not in output
    assert "■流れ" not in output
    assert "トレンド：" not in output
    assert output.index("■重要価格") < output.index("■前日評価")


def test_build_technical_output_marks_manually_supplied_prices():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(
        name="Sample",
        code4="1234",
        manual_quote=ManualTechnicalQuote(
            latest=172.0,
            high=174.0,
            low=165.0,
            vwap=170.5,
            observed_at=datetime(2026, 4, 8, 14, 32),
        ),
    )

    output = build_technical_output(result)

    assert output.startswith(
        "取得時刻：2026-04-08 14:32（手入力：現在値・高値・安値・VWAP）\n"
    )
    assert "VWAP+1.50円/" in output
    assert "(手入力)" in output
    assert "O 168.00　H 174.00　L 165.00　C 172.00" in output


def test_build_technical_output_filters_strategy_by_evaluation_time():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    preopen = build_technical_output(replace(result, evaluation_at=pd.Timestamp("2026-04-08 08:30").to_pydatetime()))
    assert "前場深押し" not in preopen
    assert "前場VWAP回復○：" in preopen
    assert "ホールド銘柄の指値売：" in preopen
    assert "後場VWAP回復○：" not in preopen

    am = build_technical_output(replace(result, evaluation_at=pd.Timestamp("2026-04-08 09:10").to_pydatetime()))
    assert "前場深押し" not in am
    assert "前場VWAP回復○：" in am
    assert "後場VWAP回復" not in am

    lunch = build_technical_output(replace(result, evaluation_at=pd.Timestamp("2026-04-08 11:45").to_pydatetime()))
    assert "前場VWAP回復" not in lunch
    assert "後場VWAP回復○：" in lunch

    pm = build_technical_output(replace(result, evaluation_at=pd.Timestamp("2026-04-08 13:00").to_pydatetime()))
    assert "後場VWAP維持/利確/持ち越し判定：" in pm
    assert "前場VWAP回復" not in pm

    closing = build_technical_output(replace(result, evaluation_at=pd.Timestamp("2026-04-08 15:10").to_pydatetime()))
    assert "持ち越し/利確：" in closing
    assert "後場VWAP維持/利確/持ち越し判定" not in closing


def test_build_technical_output_renames_rsi_divergence():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    signal = RsiSignal(55.0, 3.0, "↑", "上昇中", "中立")
    rsi_analysis = RsiAnalysis(
        five_min=signal,
        hourly=signal,
        five_min_divergence=RsiDivergence("明確な乖離なし", ""),
        hourly_divergence=RsiDivergence("上昇鈍化", "価格高値更新 / RSI未更新"),
        overall_label="上昇鈍化警戒",
    )

    output = build_technical_output(replace(result, rsi_analysis=rsi_analysis))

    assert "RSIダイバージェンス：時間足 上昇鈍化" in output
    assert "RSI乖離" not in output


def test_build_technical_output_appends_three_axis_collapse_reason():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    moving_average = replace(
        result.snapshot.moving_average,
        ma25_prev5=(result.snapshot.moving_average.ma25 or 0) + 1,
        ma5_slope=0.0,
    )
    result = replace(result, snapshot=replace(result.snapshot, moving_average=moving_average))

    output = build_technical_output(result)

    assert "短評：A1弱 上方乖離｜崩れ警戒｜監視のみ｜下行初動：5日線下向き＋25日線下向き" in output
    assert "｜下行初動：5日線下向き＋25日線下向き" in output


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

    assert "短評：C1 奪回待ち｜反転確認｜25日線奪回確認まで見送り" in output
    assert "詳細：" not in output
    assert "底打ち初動判定：成立" in output
    assert "ホールド判定：△" in output
    assert "戦略判定：\n前場VWAP回復○：反転観測強。" in output
    assert "前場深押し" not in output
    assert "前場VWAP回復○：反転観測強。" in output
    assert "後場VWAP回復○：後場VWAP上維持でも、持ち越し判断は25日線奪回後。" in output


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

    assert "短評：D1 反転初動候補・検証不足｜VWAP回復・確認不足｜件数不足｜25日線奪回待ち" in output
    assert "前場深押し" not in output
    assert "前場VWAP回復△：VWAP回復とD3化は反転観測に留め" in output


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

    assert "短評：E 25日線下｜支持線反発候補｜反転確認まで見送り" in output
    assert "前場VWAP回復△：VWAP回復帯" in output
    assert "新規は25日線奪回待ち" in output


def test_build_technical_output_marks_previous_session_intraday_na_when_missing():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: pd.DataFrame(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    output = build_technical_output(result)

    assert "前日終値：168円（VWAPN/A円／騰落率+0.6%）" in output
    assert "需給（VWAP）：当日 N/A　前日前場／後場　N/A／N/A" in output
    assert "前日Vwap(前・後場)" not in output
    assert "高値更新 〇 / 安値維持 〇" not in output
    assert "後場評価：" not in output
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

    assert "下値：168(25ME)：0.6%→165(preL)：2.4%→160(20dL/75ME)：5.3%" in output
    assert "150(60dL)" not in output.split("\n　抵抗：", 1)[0]


def test_current_risk_reward_skips_levels_too_near_latest_price():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _intraday_history(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")
    moving_average = replace(result.snapshot.moving_average, ma25=168.8)
    previous_session = replace(result.snapshot.previous_session, prev_low=165.0, prev_high=169.2)
    breakline = replace(result.snapshot.breakline, recent20_high=180.0, recent60_high=180.0)
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

    assert "下値：168.80(25ME)：0.1%→165(preL)：2.4%" in output
    assert "抵抗：169.20(preH)：0.1%→180(20dH/60dH)：6.5%" in output
    assert "リスクリターン：RR2.75" in output

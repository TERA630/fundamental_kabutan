from app.domain.builders.technical_output import build_technical_output
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

    assert "【銘柄】Sample (1234)" in output
    assert "株価：" in output
    assert "終端位置" in output
    assert "取得時刻：2026-04-07 14:55" in output
    assert "25日線解離：" in output
    assert "　傾き：↑" in output
    assert "Vwap：" in output
    assert "前場Vwap：167.17" in output
    assert "後場Vwap：167.78" in output
    assert "当日出来高：20日平均比　101%(前日出来高比　+0.1%)　通常" in output
    assert "60日レンジ位置：98.4%　高値圏 / 過熱・上値追い警戒" in output
    assert "■モメンタム" in output
    assert "3日高値更新：〇〇〇" in output
    assert "3日安値切り上げ：〇〇〇" in output
    assert "3日騰落率　+1.2%" in output
    assert "3日出来高　101%→101%→101%" in output
    assert "■当日位置・レンジ" in output
    assert "■移動平均" in output
    assert "■移動平均・出来高" not in output
    assert "出来高：1,069株" not in output
    assert "■前日評価" in output
    assert "終値 168（VWAP +0.47円 / +0.3% / 0.09ATR）騰落率+0.6%" in output
    assert "前日Vwap(前・後場)　〇/〇  高値更新 〇 / 安値維持 〇" in output
    assert "前日出来高：　20日平均比　100.9%(前々日比　+0.1%)" in output
    assert "後場評価 高値維持 / VWAP上" in output
    assert "前日レンジ 165-170（1.00ATR）　終位置 60.0%" in output
    assert "前日ローソク足型：　小陽線" in output
    assert "前日ローソク足型：　小陽線＋" not in output
    assert "■支持線" in output
    assert "20日安値：" in output
    assert "60日安値：" in output
    assert "■節目・ブレイクライン" not in output
    assert "■流れ" not in output
    assert "トレンド：" not in output


def test_build_technical_output_marks_daily_reference_vwap():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _daily_history(0),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    output = build_technical_output(result)

    assert "Vwap：" in output
    assert "取得時刻：2026-04-08 終値" in output
    assert "(日足参考値)" in output
    assert "前場Vwap：" not in output
    assert "後場Vwap：" not in output


def test_build_technical_output_marks_previous_session_intraday_na_when_missing():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: pd.DataFrame(),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    output = build_technical_output(result)

    assert "終値 168（VWAP N/A円 / N/A / N/A）騰落率+0.6%" in output
    assert "前日Vwap(前・後場)　N/A/N/A  高値更新 〇 / 安値維持 〇" in output
    assert "後場評価 N/A / VWAPN/A" in output

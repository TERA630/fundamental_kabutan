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
    assert "トレンド：" in output
    assert "25日線傾き：" in output
    assert "Vwap：" in output
    assert "前日高値：" in output
    assert "■当日位置・レンジ" in output
    assert "■移動平均・出来高" in output
    assert "20日平均出来高比" in output
    assert "出来高：1,069株" in output
    assert "■前日評価" in output
    assert "終値 168（VWAP +0.47円 / +0.3% / 0.09ATR）騰落率+0.6%" in output
    assert "前日Vwap(前・後場)　〇/〇  高値更新 〇 / 安値維持 〇" in output
    assert "前日出来高比　　100.9%" in output
    assert "後場評価 高値維持 / VWAP上" in output
    assert "前日レンジ 165-170（1.00ATR）　終位置 60.0%" in output
    assert "前日ローソク足型：　小陽線＋追加記載なし" in output
    assert "5日高値 " in output
    assert "20日高値まで：" in output
    assert "■支持線" in output
    assert "20日安値：" in output
    assert "60日安値：" in output
    assert "■節目・ブレイクライン" not in output
    assert "■流れ" not in output


def test_build_technical_output_marks_daily_reference_vwap():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _daily_history(0),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    output = build_technical_output(result)

    assert "Vwap：" in output
    assert "(日足参考値)" in output

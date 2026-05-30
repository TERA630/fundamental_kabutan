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


def test_build_technical_output_contains_summary_and_sections():
    service = TechnicalAnalysisService(
        file_cache=InMemoryCache(),
        fetch_daily_history=lambda _code4: _daily_history(),
        fetch_intraday_history=lambda _code4: _daily_history(2),
    )
    result = service.build_analysis_result(name="Sample", code4="1234")

    output = build_technical_output(result)

    assert "【銘柄】Sample (1234)" in output
    assert "株価：" in output
    assert "トレンド：" in output
    assert "Vwap：" in output
    assert "■当日位置・レンジ" in output
    assert "■移動平均・出来高" in output
    assert "■前日評価" in output
    assert "■節目・ブレイクライン" in output
    assert "■流れ" in output


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

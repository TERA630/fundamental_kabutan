from types import SimpleNamespace
from app.domain.builders.technical_output import build_technical_output
from app.domain.usecases.technical_analysis import TechnicalAnalysisService

class InMemoryCache:
    def __init__(self):
        self.store = {}
    def get(self, key, ttl_sec):
        return self.store.get(key)
    def set(self, key, value):
        self.store[key] = value

import pandas as pd

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

service = TechnicalAnalysisService(
    file_cache=InMemoryCache(),
    fetch_daily_history=lambda _code4: _daily_history(),
    fetch_intraday_history=lambda _code4: _intraday_history(),
)
result = service.build_analysis_result(name="Sample", code4="1234")
output = build_technical_output(result)
print(output)
print('--- contains collapse label? ', '崩れ 1/8：崩れ軽微' in output)

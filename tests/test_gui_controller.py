from pathlib import Path
from datetime import date
from types import SimpleNamespace

import pandas as pd

from app.data.file_cache import FileCache
from app.gui_controller import FundamentalGuiController, build_fundamental_summary_filename
from app.domain.models.market_data import MarketDataBundle, MarketSnapshot


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
    index = pd.date_range("2026-05-29 09:00", periods=2, freq="5min")
    return pd.DataFrame(
        {
            "Open": [168.0, 169.0],
            "High": [170.0, 171.0],
            "Low": [167.0, 168.0],
            "Close": [169.0, 170.0],
            "Volume": [1000.0, 2000.0],
        },
        index=index,
    )


class DummyService:
    def __init__(self):
        self.calls = []

    def build_analysis_output(self, name, code4, build_output_fn, kabutan_html_dir=None):
        self.calls.append((name, code4, kabutan_html_dir))
        return f"OUT:{name}:{code4}:{kabutan_html_dir}"


def test_fetch_analysis_output_uses_injected_service_factory(tmp_path: Path):
    dummy_service = DummyService()

    def build_service(_cache):
        return dummy_service

    controller = FundamentalGuiController(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=build_service,
    )
    output_cache = {}
    cache_key = "k1"

    out1 = controller.fetch_analysis_output(
        name="トヨタ",
        code4="7203",
        output_cache=output_cache,
        output_cache_key=cache_key,
        kabutan_html_dir=tmp_path,
    )
    out2 = controller.fetch_analysis_output(
        name="トヨタ",
        code4="7203",
        output_cache=output_cache,
        output_cache_key=cache_key,
        kabutan_html_dir=tmp_path,
    )

    assert out1 == out2
    assert len(dummy_service.calls) == 1


def test_fetch_resolved_kabutan_html_dir_uses_cache(tmp_path: Path):
    controller = FundamentalGuiController(file_cache=FileCache(base_dir=tmp_path / "cache"))
    target = tmp_path / "kabutan"
    target.mkdir()

    controller.save_kabutan_html_dir_cache(target)
    resolved = controller.fetch_resolved_kabutan_html_dir()

    assert resolved.status == "ok"
    assert resolved.dir_path == target.resolve()


def test_build_kabutan_html_package_uses_package_service(tmp_path: Path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "package"
    source_dir.mkdir()
    (source_dir / "7203.html").write_text("<html><body>7203</body></html>", encoding="utf-8")
    controller = FundamentalGuiController(file_cache=FileCache(base_dir=tmp_path / "cache"))

    result = controller.build_kabutan_html_package(source_dir=source_dir, output_dir=output_dir)

    assert result.normalized_count == 1
    assert result.html_dir == output_dir.resolve() / "html"
    assert (output_dir / "html" / "7203.html").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "kabutan_html_package.zip").exists()


def test_fetch_resolved_watchlist_path_uses_cache(tmp_path: Path):
    controller = FundamentalGuiController(file_cache=FileCache(base_dir=tmp_path / "cache"))
    target = tmp_path / "watchlist.md"
    target.write_text("トヨタ (7203)\n", encoding="utf-8")

    controller.save_watchlist_path_cache(target)
    resolved = controller.fetch_resolved_watchlist_path()

    assert resolved.status == "ok"
    assert resolved.file_path == target.resolve()


def test_build_fundamental_summary_filename_uses_date():
    assert build_fundamental_summary_filename(today=date(2026, 5, 30)) == "fundamental_summary-2026-05-30.md"


def test_build_and_save_fundamental_summary_writes_dated_filename(tmp_path: Path, monkeypatch):
    class DummySummaryService:
        def __init__(self, service):
            self.service = service

        def build_summary_table(self, watchlist_entries, *, kabutan_html_dir=None):
            assert watchlist_entries == [("トヨタ", "7203")]
            assert kabutan_html_dir == tmp_path / "html"
            return "TABLE"

    monkeypatch.setattr("app.gui_controller.FundamentalSummaryService", DummySummaryService)
    monkeypatch.setattr("app.gui_controller.build_fundamental_summary_markdown", lambda table: f"MD:{table}\n")

    controller = FundamentalGuiController(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: object(),
    )
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    output_path = controller.build_and_save_fundamental_summary(
        watchlist_entries=[("トヨタ", "7203")],
        output_dir=output_dir,
        kabutan_html_dir=tmp_path / "html",
        today=date(2026, 5, 30),
    )

    assert output_path == output_dir / "fundamental_summary-2026-05-30.md"
    assert output_path.read_text(encoding="utf-8") == "MD:TABLE\n"


def test_fetch_technical_output_uses_injected_technical_service(tmp_path: Path, monkeypatch):
    result = object()

    class DummyTechnicalService:
        def __init__(self):
            self.calls = []

        def build_analysis_result(self, *, name, code4):
            self.calls.append((name, code4))
            return result

    dummy_service = DummyTechnicalService()
    monkeypatch.setattr("app.gui_controller.build_technical_output", lambda value: "TECH" if value is result else "BAD")
    controller = FundamentalGuiController(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_technical_service=lambda _cache: dummy_service,
    )

    output = controller.fetch_technical_output(name="トヨタ", code4="7203")

    assert output == "TECH"
    assert dummy_service.calls == [("トヨタ", "7203")]


def test_default_controller_reuses_market_data_bundle_for_technical_and_summary(tmp_path: Path, monkeypatch):
    calls = {"bundle": 0}

    class DummyMarketDataService:
        def fetch_bundle(self, code4):
            calls["bundle"] += 1
            return MarketDataBundle(
                code4=code4,
                daily_history=_daily_history(),
                intraday_history=_intraday_history(),
                snapshot=MarketSnapshot(price=169.0, market_cap=3_000_000_000_000.0),
            )

    monkeypatch.setattr("app.gui_controller.build_technical_output", lambda _result: "TECH")
    controller = FundamentalGuiController(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_market_data_service=lambda _cache: DummyMarketDataService(),
    )

    output = controller.fetch_technical_output(name="トヨタ", code4="7203")
    text = controller.fetch_institutional_summary_text(name="トヨタ", code4="7203", kabutan_html_dir=None)

    assert output == "TECH"
    assert "機関投資サマリ" in text
    assert calls["bundle"] == 1


def test_fetch_institutional_summary_text_builds_panel_without_kabutan(tmp_path: Path):
    technical_result = SimpleNamespace(
        snapshot=SimpleNamespace(
            price=SimpleNamespace(close=2000.0, volume=10_000_000.0, volume_avg20=8_000_000.0, latest=2000.0),
            moving_average=SimpleNamespace(ma5=1900.0, ma25=2100.0),
        ),
        vwap_snapshot={"vwap": 1950.0, "vwap_source": "本日5分足"},
    )

    class DummyTechnicalService:
        def build_analysis_result(self, *, name, code4):
            return technical_result

    class DummyFundamentalService:
        def fetch_price_snapshot(self, code4):
            return {
                "price": 2000.0,
                "market_cap": 3_000_000_000_000.0,
                "per": None,
                "pbr": None,
                "industry": None,
                "div_yield": None,
                "payout_ratio": None,
                "as_of": None,
            }

    controller = FundamentalGuiController(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=lambda _cache: DummyFundamentalService(),
        build_technical_service=lambda _cache: DummyTechnicalService(),
    )

    text = controller.fetch_institutional_summary_text(name="トヨタ", code4="7203", kabutan_html_dir=None)

    assert "機関投資サマリ" in text
    assert "時価総額：30,000.0億円（超大型）" in text
    assert "売買代金 200.0億円" in text
    assert "機関投資スコア：10/20点" in text
    assert "Fundamental Score：N/A" in text
    assert "Technical：VWAP ○ / 5日線 ○ / 25日線 ×" in text

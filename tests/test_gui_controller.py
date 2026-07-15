from pathlib import Path
from datetime import date, datetime
from types import SimpleNamespace
import zipfile

import pandas as pd

from app.data.file_cache import FileCache
from app.domain.models.manual_technical_quote import ManualTechnicalQuote
from app.gui import _parse_manual_price
from app.services.analysis_application_service import (
    AnalysisApplicationService,
    build_fundamental_summary_filename,
    build_technical_summary_filename,
)
from app.services import stock_analysis_workflow as stock_analysis_module
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

    def build_analysis_result(self, name, code4, kabutan_html_dir=None):
        self.calls.append((name, code4, kabutan_html_dir))
        return f"OUT:{name}:{code4}:{kabutan_html_dir}"


def test_fetch_analysis_output_rebuilds_output_each_time(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(stock_analysis_module, "build_fundamental_output_from_result", lambda result: result)
    dummy_service = DummyService()

    def build_service(_cache):
        return dummy_service

    controller = AnalysisApplicationService(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_fundamental_service=build_service,
    )
    out1 = controller.fetch_analysis_output(
        name="トヨタ",
        code4="7203",
        kabutan_html_dir=tmp_path,
    )
    out2 = controller.fetch_analysis_output(
        name="トヨタ",
        code4="7203",
        kabutan_html_dir=tmp_path,
    )

    assert out1 == out2
    assert len(dummy_service.calls) == 2


def test_fetch_resolved_kabutan_html_dir_uses_cache(tmp_path: Path):
    controller = AnalysisApplicationService(file_cache=FileCache(base_dir=tmp_path / "cache"))
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
    controller = AnalysisApplicationService(file_cache=FileCache(base_dir=tmp_path / "cache"))

    result = controller.build_kabutan_html_package(source_dir=source_dir, output_dir=output_dir)

    assert result.normalized_count == 1
    assert result.html_dir == output_dir.resolve() / "html"
    assert (output_dir / "html" / "7203.html").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "kabutan_html_package.zip").exists()


def test_import_kabutan_html_package_uses_package_service(tmp_path: Path):
    zip_path = tmp_path / "package.zip"
    output_dir = tmp_path / "imported"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("html/7203.html", "<html></html>")
    controller = AnalysisApplicationService(file_cache=FileCache(base_dir=tmp_path / "cache"))

    result = controller.import_kabutan_html_package(zip_path=zip_path, output_dir=output_dir)

    assert result.html_dir == output_dir.resolve() / "html"
    assert result.manifest_path == output_dir.resolve() / "manifest.json"
    assert result.html_count == 1


def test_resolve_imported_kabutan_package_imports_once_and_reuses_html_dir(tmp_path: Path):
    zip_path = tmp_path / "package.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("html/7203.html", "<html></html>")
    controller = AnalysisApplicationService(file_cache=FileCache(base_dir=tmp_path / "cache"))

    first = controller.resolve_imported_kabutan_package(
        zip_path=zip_path,
        current_signature=None,
        current_html_dir=None,
    )
    second = controller.resolve_imported_kabutan_package(
        zip_path=zip_path,
        current_signature=first.signature,
        current_html_dir=first.html_dir,
    )

    assert first.imported is True
    assert first.html_dir.exists()
    assert second.imported is False
    assert second.html_dir == first.html_dir


def test_fetch_resolved_watchlist_path_uses_cache(tmp_path: Path):
    controller = AnalysisApplicationService(file_cache=FileCache(base_dir=tmp_path / "cache"))
    target = tmp_path / "watchlist.md"
    target.write_text("トヨタ (7203)\n", encoding="utf-8")

    controller.save_watchlist_path_cache(target)
    resolved = controller.fetch_resolved_watchlist_path()

    assert resolved.status == "ok"
    assert resolved.file_path == target.resolve()


def test_build_fundamental_summary_filename_uses_date():
    assert build_fundamental_summary_filename(today=date(2026, 5, 30)) == "fundamental_summary-2026-05-30.md"


def test_build_technical_summary_filename_uses_month_day_hour_minute():
    assert (
        build_technical_summary_filename(generated_at=datetime(2026, 5, 30, 14, 5))
        == "technical_summary_05-30-14-05.md"
    )


def test_build_and_save_fundamental_summary_writes_dated_filename(tmp_path: Path, monkeypatch):
    class DummySummaryService:
        def __init__(self, service):
            self.service = service

        def build_summary_table(self, watchlist_entries, *, kabutan_html_dir=None):
            assert watchlist_entries == [("トヨタ", "7203")]
            assert kabutan_html_dir == tmp_path / "html"
            return "TABLE"

    monkeypatch.setattr("app.services.summary_workflow.FundamentalSummaryService", DummySummaryService)
    monkeypatch.setattr("app.services.summary_workflow.build_fundamental_summary_markdown", lambda table: f"MD:{table}\n")

    controller = AnalysisApplicationService(
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


def test_build_and_save_technical_summary_writes_dated_filename(tmp_path: Path, monkeypatch):
    class DummySummaryService:
        def __init__(self, build_result, build_us_market_summary=None):
            self.build_result = build_result
            self.build_us_market_summary = build_us_market_summary

        def build_summary_table(self, watchlist_entries):
            assert watchlist_entries == [("トヨタ", "7203")]
            return "TECH_TABLE"

    monkeypatch.setattr("app.services.summary_workflow.TechnicalSummaryService", DummySummaryService)
    monkeypatch.setattr("app.services.summary_workflow.build_technical_summary_markdown", lambda table: f"TECH_MD:{table}\n")

    controller = AnalysisApplicationService(file_cache=FileCache(base_dir=tmp_path / "cache"))
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    output_path = controller.build_and_save_technical_summary(
        watchlist_entries=[("トヨタ", "7203")],
        output_dir=output_dir,
        generated_at=datetime(2026, 5, 30, 14, 5),
    )

    assert output_path == output_dir / "technical_summary_05-30-14-05.md"
    assert output_path.read_text(encoding="utf-8") == "TECH_MD:TECH_TABLE\n"


def test_fetch_technical_output_uses_injected_technical_service(tmp_path: Path, monkeypatch):
    result = object()

    class DummyTechnicalService:
        def __init__(self):
            self.calls = []

        def build_analysis_result(self, *, name, code4):
            self.calls.append((name, code4))
            return result

    dummy_service = DummyTechnicalService()
    monkeypatch.setattr("app.services.stock_analysis_workflow.build_technical_output", lambda value: "TECH" if value is result else "BAD")
    controller = AnalysisApplicationService(
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

    monkeypatch.setattr("app.services.stock_analysis_workflow.build_technical_output", lambda _result: "TECH")
    controller = AnalysisApplicationService(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_market_data_service=lambda _cache: DummyMarketDataService(),
    )

    output = controller.fetch_technical_output(name="トヨタ", code4="7203")
    text = controller.fetch_institutional_summary_text(name="トヨタ", code4="7203", kabutan_html_dir=None)

    assert output == "TECH"
    assert "機関投資サマリ" in text
    assert calls["bundle"] == 1


def test_default_controller_bypasses_memory_cache_for_latest_technical_output(tmp_path: Path, monkeypatch):
    calls = {"bundle": 0}

    class DummyMarketDataService:
        def fetch_bundle(self, code4):
            calls["bundle"] += 1
            return MarketDataBundle(
                code4=code4,
                daily_history=_daily_history(),
                intraday_history=_intraday_history(),
                snapshot=MarketSnapshot(price=169.0),
            )

    monkeypatch.setattr("app.services.stock_analysis_workflow.build_technical_output", lambda _result: "TECH")
    controller = AnalysisApplicationService(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_market_data_service=lambda _cache: DummyMarketDataService(),
    )

    first = controller.fetch_technical_output(name="トヨタ", code4="7203")
    second = controller.fetch_technical_output(name="トヨタ", code4="7203")

    assert first == "TECH"
    assert second == "TECH"
    assert calls["bundle"] == 2


def test_default_controller_reanalyzes_with_manual_technical_quote(tmp_path: Path):
    class DummyMarketDataService:
        def fetch_bundle(self, code4):
            return MarketDataBundle(
                code4=code4,
                daily_history=_daily_history(),
                intraday_history=_intraday_history(),
                snapshot=MarketSnapshot(price=169.0),
            )

    controller = AnalysisApplicationService(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_market_data_service=lambda _cache: DummyMarketDataService(),
    )
    detail = controller.fetch_technical_output_result(
        name="トヨタ",
        code4="7203",
        manual_quote=ManualTechnicalQuote(
            latest=172.0,
            high=174.0,
            low=165.0,
            vwap=170.5,
            observed_at=datetime(2026, 4, 8, 14, 32),
        ),
    )

    assert detail.analysis_result.evaluation_price == 172.0
    assert detail.analysis_result.vwap_snapshot["vwap"] == 170.5
    assert "手入力：現在値・高値・安値・VWAP" in detail.output


def test_parse_manual_price_accepts_commas_and_full_width_numbers():
    assert _parse_manual_price("１，２３４．５", "当日現在値") == 1234.5


def test_default_controller_bypasses_memory_cache_for_technical_timestamp_choices(tmp_path: Path):
    calls = {"bundle": 0}

    class DummyMarketDataService:
        def fetch_bundle(self, code4):
            calls["bundle"] += 1
            return MarketDataBundle(
                code4=code4,
                daily_history=_daily_history(),
                intraday_history=_intraday_history(),
                snapshot=MarketSnapshot(price=169.0),
            )

    controller = AnalysisApplicationService(
        file_cache=FileCache(base_dir=tmp_path / "cache"),
        build_market_data_service=lambda _cache: DummyMarketDataService(),
    )

    first = controller.fetch_technical_evaluation_timestamps("7203")
    second = controller.fetch_technical_evaluation_timestamps("7203")

    assert first == second
    assert calls["bundle"] == 2


def test_fetch_institutional_summary_text_builds_panel_without_kabutan(tmp_path: Path):
    technical_result = SimpleNamespace(
        snapshot=SimpleNamespace(
            price=SimpleNamespace(close=2000.0, volume=10_000_000.0, volume_avg20=8_000_000.0, latest=2000.0),
            moving_average=SimpleNamespace(ma25=2100.0),
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

    controller = AnalysisApplicationService(
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
    assert "Technical：" not in text
    assert "VWAP" not in text
    assert "25日線" not in text

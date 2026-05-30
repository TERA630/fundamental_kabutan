from pathlib import Path
from datetime import date
from types import SimpleNamespace

from app.data.file_cache import FileCache
from app.gui_controller import FundamentalGuiController, build_fundamental_summary_filename


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


def test_fetch_resolved_watchlist_path_uses_cache(tmp_path: Path):
    controller = FundamentalGuiController(file_cache=FileCache(base_dir=tmp_path / "cache"))
    target = tmp_path / "watchlist.md"
    target.write_text("トヨタ (7203)\n", encoding="utf-8")

    controller.save_watchlist_path_cache(target)
    resolved = controller.fetch_resolved_watchlist_path()

    assert resolved.status == "ok"
    assert resolved.file_path == target.resolve()


def test_build_fundamental_summary_filename_uses_date():
    assert build_fundamental_summary_filename(today=date(2026, 5, 30)) == "fundamental_summery-2026-05-30.md"


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

    assert output_path == output_dir / "fundamental_summery-2026-05-30.md"
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

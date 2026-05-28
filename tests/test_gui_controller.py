from pathlib import Path

from app.data.file_cache import FileCache
from app.gui_controller import FundamentalGuiController


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

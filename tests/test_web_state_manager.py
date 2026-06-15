from pathlib import Path
from types import SimpleNamespace

from app.web_state import WebUiState, WebUiStateManager


class FakeController:
    def __init__(self):
        self.saved_watchlist_path = None
        self.saved_kabutan_dir = None
        self.cleared_zip_cache = False
        self.fetch_call = None

    def save_watchlist_path_cache(self, path):
        self.saved_watchlist_path = path

    def save_kabutan_html_dir_cache(self, path):
        self.saved_kabutan_dir = path

    def clear_kabutan_package_zip_cache(self):
        self.cleared_zip_cache = True

    def fetch_output_for_mode(self, **kwargs):
        self.fetch_call = kwargs
        return SimpleNamespace(output="OUTPUT", institutional_summary="SUMMARY")


def test_load_watchlist_updates_state_and_selects_first(tmp_path: Path):
    controller = FakeController()
    state = WebUiState(controller=controller)
    manager = WebUiStateManager(state)
    path = tmp_path / "watchlist.md"

    manager.load_watchlist(watchlist=[("トヨタ", "7203"), ("任天堂", "7974")], path=path)

    assert state.watchlist_path == path
    assert state.selected_label == "トヨタ (7203)"
    assert controller.saved_watchlist_path == path
    assert "2" in state.status


def test_set_kabutan_html_dir_clears_package_and_output_cache(tmp_path: Path):
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.kabutan_package_zip_path = tmp_path / "package.zip"
    state.kabutan_package_zip_signature = (1, "abc")
    state.output_cache = {"cached": "output"}
    manager = WebUiStateManager(state)
    html_dir = tmp_path / "html"

    manager.set_kabutan_html_dir(html_dir)

    assert state.kabutan_html_dir == html_dir
    assert state.kabutan_package_zip_path is None
    assert state.kabutan_package_zip_signature is None
    assert state.output_cache == {}
    assert controller.saved_kabutan_dir == html_dir
    assert controller.cleared_zip_cache is True


def test_fetch_output_for_current_selection_uses_screen_state(tmp_path: Path):
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.selected_label = "トヨタ (7203)"
    state.mode = "fundamental"
    state.kabutan_html_dir = tmp_path / "html"
    manager = WebUiStateManager(state)

    assert manager.fetch_output_for_current_selection() is True

    assert state.output == "OUTPUT"
    assert state.institutional_summary == "SUMMARY"
    assert controller.fetch_call["name"] == "トヨタ"
    assert controller.fetch_call["code4"] == "7203"
    assert controller.fetch_call["mode"] == "fundamental"
    assert controller.fetch_call["kabutan_html_dir"] == tmp_path / "html"

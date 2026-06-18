from pathlib import Path
from types import SimpleNamespace
from datetime import datetime

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


class FakeTechnicalTimestampController(FakeController):
    def fetch_technical_evaluation_timestamps(self, code4):
        assert code4 == "7203"
        return (
            datetime(2026, 5, 28, 9, 0),
            datetime(2026, 5, 28, 9, 5),
            datetime(2026, 5, 29, 9, 10),
        )


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


def test_set_kabutan_html_dir_clears_package_cache(tmp_path: Path):
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.kabutan_package_zip_path = tmp_path / "package.zip"
    state.kabutan_package_zip_signature = (1, "abc")
    manager = WebUiStateManager(state)
    html_dir = tmp_path / "html"

    manager.set_kabutan_html_dir(html_dir)

    assert state.kabutan_html_dir == html_dir
    assert state.kabutan_package_zip_path is None
    assert state.kabutan_package_zip_signature is None
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


def test_fetch_output_for_current_selection_passes_technical_evaluation_at():
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.selected_label = "トヨタ (7203)"
    state.mode = "technical"
    state.technical_evaluation_date = "2026-05-29"
    state.technical_evaluation_time = "09:10"
    manager = WebUiStateManager(state)

    assert manager.fetch_output_for_current_selection() is True

    assert controller.fetch_call["evaluation_at"] == datetime(2026, 5, 29, 9, 10)
    assert "評価時点=2026-05-29 09:10" in state.status


def test_refresh_technical_evaluation_choices_groups_times_by_date():
    controller = FakeTechnicalTimestampController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.selected_label = "トヨタ (7203)"
    state.mode = "technical"
    state.technical_evaluation_date = "2026-05-28"
    manager = WebUiStateManager(state)

    manager.refresh_technical_evaluation_choices()

    assert state.technical_evaluation_date_choices == ["2026-05-29", "2026-05-28"]
    assert state.technical_evaluation_time_choices == ["09:00", "09:05"]
    assert state.technical_evaluation_time_choices_by_date == {
        "2026-05-28": ["09:00", "09:05"],
        "2026-05-29": ["09:10"],
    }


def test_technical_evaluation_at_rejects_time_missing_for_selected_date():
    state = WebUiState(controller=FakeController())
    state.mode = "technical"
    state.technical_evaluation_date = "2026-05-29"
    state.technical_evaluation_time = "09:00"
    state.technical_evaluation_time_choices_by_date = {"2026-05-29": ["09:10"]}
    manager = WebUiStateManager(state)

    assert manager.technical_evaluation_at() is None
    assert manager.technical_evaluation_label() == "最新"


def test_technical_evaluation_label_formats_valid_selection():
    state = WebUiState(controller=FakeController())
    state.mode = "technical"
    state.technical_evaluation_date = "2026-05-29"
    state.technical_evaluation_time = "09:10"
    state.technical_evaluation_time_choices_by_date = {"2026-05-29": ["09:10"]}
    manager = WebUiStateManager(state)

    assert manager.technical_evaluation_label() == "2026-05-29 09:10"

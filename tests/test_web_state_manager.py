from pathlib import Path
from types import SimpleNamespace
from datetime import datetime

from app.domain.models.watchlist import WatchlistEntry
from app.web_state import WebUiState, WebUiStateManager


class FakeController:
    def __init__(self):
        self.saved_watchlist_path = None
        self.saved_kabutan_dir = None
        self.cleared_zip_cache = False
        self.fetch_call = None
        self.summary_call = None
        self.sector_output_call = None
        self.hybrid_evaluation_call = None

    def save_watchlist_path_cache(self, path):
        self.saved_watchlist_path = path

    def save_kabutan_html_dir_cache(self, path):
        self.saved_kabutan_dir = path

    def clear_kabutan_package_zip_cache(self):
        self.cleared_zip_cache = True

    def fetch_output_for_mode(self, **kwargs):
        self.fetch_call = kwargs
        return SimpleNamespace(output="OUTPUT", institutional_summary="SUMMARY")

    def build_summary_table_for_mode(self, **kwargs):
        self.summary_call = kwargs
        return "SUMMARY_TABLE"

    def build_technical_sector_breadth_output(self, **kwargs):
        self.sector_output_call = kwargs
        return "SECTOR_OUTPUT"

    def build_single_stock_hybrid_evaluation_output(self, **kwargs):
        self.hybrid_evaluation_call = kwargs
        return "HYBRID_EVALUATION"


class FakeTechnicalTimestampController(FakeController):
    def fetch_technical_evaluation_timestamps(self, code4):
        assert code4 == "7203"
        return (
            datetime(2026, 5, 28, 9, 0),
            datetime(2026, 5, 28, 9, 5),
            datetime(2026, 5, 29, 9, 10),
        )


class FakeTechnicalResultController(FakeController):
    def fetch_technical_output_result(self, **kwargs):
        self.fetch_call = kwargs
        return SimpleNamespace(output="OUTPUT", analysis_result=object())

    def fetch_institutional_summary_text(self, **kwargs):
        self.institutional_call = kwargs
        return "SUMMARY"


def test_load_watchlist_updates_state_and_selects_first(tmp_path: Path):
    controller = FakeController()
    state = WebUiState(controller=controller)
    manager = WebUiStateManager(state)
    path = tmp_path / "watchlist.md"

    sector_entries = [
        WatchlistEntry(name="トヨタ", code4="7203", sectors=("商社・資源",)),
        WatchlistEntry(name="任天堂", code4="7974"),
    ]

    manager.load_watchlist(
        watchlist=[entry.as_tuple() for entry in sector_entries],
        watchlist_with_sectors=sector_entries,
        path=path,
    )

    assert state.watchlist_path == path
    assert state.watchlist_with_sectors == sector_entries
    assert state.selected_label == "トヨタ (7203)"
    assert controller.saved_watchlist_path == path
    assert "2" in state.status


def test_technical_summary_uses_sector_watchlist_entries():
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.mode = "technical"
    state.watchlist = [("トヨタ", "7203")]
    state.watchlist_with_sectors = [WatchlistEntry(name="トヨタ", code4="7203", sectors=("商社・資源",))]
    manager = WebUiStateManager(state)

    assert manager.build_summary_table_for_current_mode() == "SUMMARY_TABLE"

    assert controller.summary_call["mode"] == "technical"
    assert controller.summary_call["watchlist_entries"] == state.watchlist_with_sectors


def test_hybrid_evaluation_uses_selected_stock_and_forced_technical_evaluation(tmp_path: Path):
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.mode = "fundamental"
    state.watchlist = [("トヨタ", "7203")]
    state.selected_label = "トヨタ (7203)"
    state.kabutan_html_dir = tmp_path / "html"
    state.technical_evaluation_date = "2026-05-29"
    state.technical_evaluation_time = "09:10"
    manager = WebUiStateManager(state)

    assert manager.build_hybrid_evaluation_output_for_current_selection() == "HYBRID_EVALUATION"

    assert controller.hybrid_evaluation_call["name"] == "トヨタ"
    assert controller.hybrid_evaluation_call["code4"] == "7203"
    assert controller.hybrid_evaluation_call["kabutan_html_dir"] == tmp_path / "html"
    assert controller.hybrid_evaluation_call["evaluation_at"] == datetime(2026, 5, 29, 9, 10)


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


def test_fetch_output_for_current_selection_does_not_append_sector_breadth_by_default():
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.watchlist_with_sectors = [WatchlistEntry(name="トヨタ", code4="7203", sectors=("商社・資源",))]
    state.selected_label = "トヨタ (7203)"
    state.mode = "technical"
    state.technical_evaluation_date = "2026-05-29"
    state.technical_evaluation_time = "09:10"
    manager = WebUiStateManager(state)

    assert manager.fetch_output_for_current_selection() is True

    assert state.output == "OUTPUT"
    assert controller.sector_output_call is None


def test_sector_breadth_output_uses_selected_stock_sector_and_evaluation_at():
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.watchlist_with_sectors = [WatchlistEntry(name="トヨタ", code4="7203", sectors=("商社・資源",))]
    state.selected_label = "トヨタ (7203)"
    state.mode = "fundamental"
    state.technical_evaluation_date = "2026-05-29"
    state.technical_evaluation_time = "09:10"
    manager = WebUiStateManager(state)

    assert manager.build_sector_breadth_output_for_current_selection() == "SECTOR_OUTPUT"

    assert controller.sector_output_call["watchlist_entries"] == state.watchlist_with_sectors
    assert controller.sector_output_call["code4"] == "7203"
    assert controller.sector_output_call["evaluation_at"] == datetime(2026, 5, 29, 9, 10)


def test_fetch_output_for_current_selection_with_technical_result_does_not_append_sector_breadth():
    controller = FakeTechnicalResultController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.watchlist_with_sectors = [WatchlistEntry(name="トヨタ", code4="7203", sectors=("商社・資源",))]
    state.selected_label = "トヨタ (7203)"
    state.mode = "technical"
    manager = WebUiStateManager(state)

    assert manager.fetch_output_for_current_selection() is True

    assert state.output == "OUTPUT"
    assert controller.fetch_call["name"] == "トヨタ"
    assert controller.sector_output_call is None


def test_fetch_output_for_current_selection_can_keep_summary_html():
    controller = FakeController()
    state = WebUiState(controller=controller)
    state.watchlist = [("トヨタ", "7203")]
    state.selected_label = "トヨタ (7203)"
    state.mode = "technical"
    state.fundamental_summary_html = '<section class="summary-output">Summary</section>'
    manager = WebUiStateManager(state)

    assert manager.fetch_output_for_current_selection(clear_summary=False) is True

    assert state.fundamental_summary_html == '<section class="summary-output">Summary</section>'


def test_select_stock_by_code4_updates_selected_label():
    state = WebUiState(controller=FakeController())
    state.watchlist = [("トヨタ", "7203"), ("任天堂", "7974")]
    manager = WebUiStateManager(state)

    assert manager.select_stock_by_code4("7974") is True

    assert state.selected_label == "任天堂 (7974)"


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


def test_technical_evaluation_at_uses_selected_dates_latest_bar_when_time_is_latest():
    state = WebUiState(controller=FakeController())
    state.mode = "technical"
    state.technical_evaluation_date = "2026-06-19"
    state.technical_evaluation_time_choices_by_date = {"2026-06-19": ["09:00", "14:00", "15:20"]}
    manager = WebUiStateManager(state)

    assert manager.technical_evaluation_at() == datetime(2026, 6, 19, 15, 20)
    assert manager.technical_evaluation_label() == "2026-06-19 15:20"

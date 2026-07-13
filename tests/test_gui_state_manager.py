from pathlib import Path
from datetime import date, datetime

from app.domain.models.watchlist import WatchlistEntry
from app.domain.usecases.kabutan_html_dir import ResolvedKabutanHtmlDir
from app.domain.usecases.watchlist_path import ResolvedWatchlistPath
from app.gui_state import GuiState
from app.gui_state_manager import GuiStateManager
from app.gui_view_model import GuiViewModel


class FakeController:
    def __init__(self):
        self.saved_watchlist_path = None
        self.saved_kabutan_dir = None
        self.watchlist_path = None
        self.kabutan_dir = None

    def fetch_watchlist_entries(self, _path):
        return [("トヨタ", "7203"), ("任天堂", "7974")]

    def fetch_watchlist_entries_with_sectors(self, _path):
        return [
            WatchlistEntry(name="トヨタ", code4="7203", sectors=("商社・資源",)),
            WatchlistEntry(name="任天堂", code4="7974"),
        ]

    def save_watchlist_path_cache(self, path):
        self.saved_watchlist_path = path

    def fetch_resolved_watchlist_path(self):
        if self.watchlist_path is None:
            return ResolvedWatchlistPath(status="missing", file_path=None, message="")
        return ResolvedWatchlistPath(status="ok", file_path=self.watchlist_path, message="ok")

    def save_kabutan_html_dir_cache(self, path):
        self.saved_kabutan_dir = path

    def fetch_resolved_kabutan_html_dir(self):
        if self.kabutan_dir is None:
            return ResolvedKabutanHtmlDir(status="missing", dir_path=None, message="")
        return ResolvedKabutanHtmlDir(status="ok", dir_path=self.kabutan_dir, message="restored")

    def fetch_technical_evaluation_timestamps(self, code4):
        assert code4 == "7203"
        return (
            datetime(2026, 5, 28, 9, 0),
            datetime(2026, 5, 28, 9, 5),
            datetime(2026, 5, 29, 9, 10),
        )


def build_manager(controller: FakeController, state: GuiState | None = None) -> GuiStateManager:
    return GuiStateManager(
        state=state or GuiState(),
        controller=controller,
        view_model=GuiViewModel(),
    )


def test_load_watchlist_updates_state_choices(tmp_path: Path):
    controller = FakeController()
    state = GuiState()
    manager = build_manager(controller, state)
    watchlist_path = tmp_path / "watchlist.md"

    choices = manager.load_watchlist(watchlist_path)

    assert choices == ["トヨタ (7203)", "任天堂 (7974)"]
    assert state.watchlist_path == watchlist_path
    assert state.watchlist == [("トヨタ", "7203"), ("任天堂", "7974")]
    assert state.watchlist_with_sectors[0].sectors == ("商社・資源",)
    assert state.technical_watchlist_entries() == state.watchlist_with_sectors
    assert state.display_to_code["トヨタ (7203)"] == ("トヨタ", "7203")
    assert controller.saved_watchlist_path == watchlist_path


def test_restore_kabutan_html_dir_updates_state(tmp_path: Path):
    controller = FakeController()
    controller.kabutan_dir = tmp_path / "kabutan"
    manager = build_manager(controller)

    restored = manager.restore_kabutan_html_dir()

    assert restored == (controller.kabutan_dir, "restored")
    assert manager.state.kabutan_html_dir == controller.kabutan_dir


def test_refresh_technical_evaluation_choices_groups_times_by_date(tmp_path: Path):
    controller = FakeController()
    state = GuiState()
    manager = build_manager(controller, state)
    manager.load_watchlist(tmp_path / "watchlist.md")
    state.technical_evaluation_date = "2026-05-28"

    manager.refresh_technical_evaluation_choices("トヨタ (7203)")

    assert state.technical_evaluation_date_choices == ["2026-05-29", "2026-05-28"]
    assert state.technical_evaluation_time_choices == ["09:00", "09:05"]
    assert state.technical_evaluation_time_choices_by_date == {
        "2026-05-28": ["09:00", "09:05"],
        "2026-05-29": ["09:10"],
    }


def test_selected_historical_date_loads_intraday_times_on_demand(tmp_path: Path):
    class OnDemandController(FakeController):
        def __init__(self):
            super().__init__()
            self.timestamp_calls = []

        def fetch_technical_evaluation_dates(self, code4):
            assert code4 == "7203"
            return (date(2026, 5, 29), date(2026, 5, 28))

        def fetch_technical_evaluation_timestamps(self, code4, evaluation_date):
            self.timestamp_calls.append((code4, evaluation_date))
            return (
                datetime(2026, 5, 28, 9, 0),
                datetime(2026, 5, 28, 14, 0),
                datetime(2026, 5, 29, 9, 0),
            )

    controller = OnDemandController()
    state = GuiState()
    manager = build_manager(controller, state)
    manager.load_watchlist(tmp_path / "watchlist.md")

    manager.refresh_technical_evaluation_choices("トヨタ (7203)")
    assert state.technical_evaluation_date_choices == ["2026-05-29", "2026-05-28"]
    assert controller.timestamp_calls == []

    manager.set_technical_evaluation_selection(date_text="2026-05-28", time_text="最新")
    manager.load_technical_times_for_selected_date("トヨタ (7203)")
    manager.update_technical_time_choices_for_selected_date()

    assert controller.timestamp_calls == [("7203", date(2026, 5, 28))]
    assert state.technical_evaluation_time_choices == ["09:00", "14:00"]


def test_technical_evaluation_at_uses_valid_gui_selection(tmp_path: Path):
    controller = FakeController()
    state = GuiState()
    manager = build_manager(controller, state)
    manager.load_watchlist(tmp_path / "watchlist.md")
    manager.refresh_technical_evaluation_choices("トヨタ (7203)")
    manager.set_technical_evaluation_selection(date_text="2026-05-29", time_text="09:10")

    assert manager.technical_evaluation_at() == datetime(2026, 5, 29, 9, 10)
    assert manager.technical_evaluation_label() == "2026-05-29 09:10"


def test_technical_evaluation_at_uses_selected_dates_latest_bar_when_time_is_latest():
    state = GuiState(
        technical_evaluation_date="2026-06-19",
        technical_evaluation_time_choices_by_date={"2026-06-19": ["09:00", "14:00", "15:20"]},
    )
    manager = build_manager(FakeController(), state)

    assert manager.technical_evaluation_at() == datetime(2026, 6, 19, 15, 20)
    assert manager.technical_evaluation_label() == "2026-06-19 15:20"


def test_date_change_defaults_gui_time_to_1400_when_available():
    state = GuiState(
        technical_evaluation_date="2026-06-19",
        technical_evaluation_time_choices_by_date={"2026-06-19": ["09:00", "14:00", "14:05", "15:20"]},
    )
    manager = build_manager(FakeController(), state)

    manager.update_technical_time_choices_for_selected_date()

    assert state.technical_evaluation_time == "14:00"


def test_technical_evaluation_at_rejects_invalid_gui_date_time_pair():
    state = GuiState(
        technical_evaluation_date="2026-05-29",
        technical_evaluation_time="09:00",
        technical_evaluation_time_choices_by_date={"2026-05-29": ["09:10"]},
    )
    manager = build_manager(FakeController(), state)

    assert manager.technical_evaluation_at() is None
    assert manager.technical_evaluation_label() == "最新"

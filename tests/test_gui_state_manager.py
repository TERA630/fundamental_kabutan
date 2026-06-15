from pathlib import Path

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
    assert state.display_to_code["トヨタ (7203)"] == ("トヨタ", "7203")
    assert controller.saved_watchlist_path == watchlist_path


def test_restore_kabutan_html_dir_updates_state(tmp_path: Path):
    controller = FakeController()
    controller.kabutan_dir = tmp_path / "kabutan"
    manager = build_manager(controller)

    restored = manager.restore_kabutan_html_dir()

    assert restored == (controller.kabutan_dir, "restored")
    assert manager.state.kabutan_html_dir == controller.kabutan_dir

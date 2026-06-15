"""State transition helpers for the Tkinter GUI."""

from __future__ import annotations

from pathlib import Path

from app.gui_state import GuiState
from app.gui_view_model import GuiViewModel
from app.services.analysis_application_service import AnalysisApplicationService
from app.ui_state_utils import build_stock_choices, get_selected_stock


class GuiStateManager:
    def __init__(
        self,
        *,
        state: GuiState,
        controller: AnalysisApplicationService,
        view_model: GuiViewModel,
    ):
        self.state = state
        self.controller = controller
        self.view_model = view_model

    def load_watchlist(self, path: Path) -> list[str]:
        watchlist = self.controller.fetch_watchlist_entries(path)
        self.state.watchlist_path = path
        self.controller.save_watchlist_path_cache(path)
        self.state.watchlist = watchlist
        return self.rebuild_stock_choices()

    def restore_watchlist(self) -> tuple[Path, list[str], str] | None:
        resolved = self.controller.fetch_resolved_watchlist_path()
        if resolved.status != "ok" or resolved.file_path is None:
            return None
        watchlist = self.controller.fetch_watchlist_entries(resolved.file_path)
        self.state.watchlist_path = resolved.file_path
        self.state.watchlist = watchlist
        choices = self.rebuild_stock_choices()
        status = self.view_model.build_watchlist_restored_status(len(watchlist))
        return resolved.file_path, choices, status

    def select_kabutan_html_dir(self, path: Path) -> str:
        self.state.kabutan_html_dir = path
        self.controller.save_kabutan_html_dir_cache(path)
        return self.view_model.build_kabutan_dir_selected_status()

    def restore_kabutan_html_dir(self) -> tuple[Path, str] | None:
        resolved = self.controller.fetch_resolved_kabutan_html_dir()
        if resolved.status != "ok" or resolved.dir_path is None:
            return None
        self.state.kabutan_html_dir = resolved.dir_path
        return resolved.dir_path, resolved.message

    def rebuild_stock_choices(self) -> list[str]:
        values, mapping = build_stock_choices(self.state.watchlist)
        self.state.display_to_code = mapping
        return values

    def selected_stock(self, selected_label: str) -> tuple[str, str] | None:
        return get_selected_stock(self.state.display_to_code, selected_label)

__all__ = ["GuiStateManager"]

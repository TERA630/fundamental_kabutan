"""Web UI state and state management helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.gui_controller import FundamentalGuiController
from app.gui_state_utils import build_stock_choices, get_selected_stock
from app.gui_view_model import GuiViewModel

DEFAULT_INSTITUTIONAL_SUMMARY = "機関投資サマリ\n時価総額：N/A\n流動性：N/A\n機関投資スコア：N/A"


@dataclass
class WebUiState:
    controller: FundamentalGuiController = field(default_factory=FundamentalGuiController)
    view_model: GuiViewModel = field(default_factory=GuiViewModel)
    watchlist_path: Path | None = None
    kabutan_html_dir: Path | None = None
    kabutan_package_zip_path: Path | None = None
    watchlist: list[tuple[str, str]] = field(default_factory=list)
    output_cache: dict[str, str] = field(default_factory=dict)
    selected_label: str = ""
    mode: str = "fundamental"
    output: str = ""
    institutional_summary: str = DEFAULT_INSTITUTIONAL_SUMMARY
    fundamental_summary_html: str = ""
    summary_kind: str = ""
    summary_markdown: str = ""
    summary_html: str = ""
    summary_filename: str = ""
    status: str = field(default_factory=GuiViewModel.build_initial_status)

    @property
    def stock_choices(self) -> list[str]:
        choices, _mapping = build_stock_choices(self.watchlist)
        return choices


class WebUiStateManager:
    def __init__(self, state: WebUiState):
        self.state = state

    def restore_cached_state(self) -> None:
        state = self.state
        state.output_cache = state.controller.fetch_output_cache_for_today()
        resolved_watchlist = state.controller.fetch_resolved_watchlist_path()
        if resolved_watchlist.status == "ok" and resolved_watchlist.file_path is not None:
            try:
                state.watchlist_path = resolved_watchlist.file_path
                state.watchlist = state.controller.fetch_watchlist_entries(resolved_watchlist.file_path)
                state.status = state.view_model.build_watchlist_restored_status(len(state.watchlist))
                self.select_first_if_needed()
            except Exception:
                state.watchlist_path = None
                state.watchlist = []

        state.kabutan_package_zip_path = state.controller.fetch_kabutan_package_zip_cache()

    def select_first_if_needed(self) -> None:
        choices = self.state.stock_choices
        if choices and self.state.selected_label not in choices:
            self.state.selected_label = choices[0]

    def sync_form_selection(self, selected_stock_label: str | None, mode: str | None) -> None:
        if selected_stock_label is not None:
            self.state.selected_label = selected_stock_label
        if mode is not None:
            self.state.mode = mode

    def selected_stock(self) -> tuple[str, str] | None:
        _, mapping = build_stock_choices(self.state.watchlist)
        return get_selected_stock(mapping, self.state.selected_label)

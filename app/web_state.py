"""Web UI state and state management helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.gui_view_model import GuiViewModel
from app.services.analysis_application_service import AnalysisApplicationService
from app.ui_state_utils import build_output_cache_key, build_stock_choices, get_selected_stock

DEFAULT_INSTITUTIONAL_SUMMARY = "機関投資サマリ\n時価総額：N/A\n流動性：N/A\n機関投資スコア：N/A"


@dataclass
class WebUiState:
    controller: AnalysisApplicationService = field(default_factory=AnalysisApplicationService)
    view_model: GuiViewModel = field(default_factory=GuiViewModel)
    watchlist_path: Path | None = None
    kabutan_html_dir: Path | None = None
    kabutan_package_zip_path: Path | None = None
    kabutan_package_zip_signature: tuple[int, str] | tuple[int, int] | None = None
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

        fetch_resolved_kabutan_html_dir = getattr(state.controller, "fetch_resolved_kabutan_html_dir", None)
        if callable(fetch_resolved_kabutan_html_dir):
            resolved_kabutan_dir = fetch_resolved_kabutan_html_dir()
            if resolved_kabutan_dir.status == "ok" and resolved_kabutan_dir.dir_path is not None:
                state.kabutan_html_dir = resolved_kabutan_dir.dir_path

        fetch_kabutan_package_zip_cache = getattr(state.controller, "fetch_kabutan_package_zip_cache", None)
        if callable(fetch_kabutan_package_zip_cache):
            state.kabutan_package_zip_path = fetch_kabutan_package_zip_cache()
            if state.kabutan_package_zip_path is not None:
                try:
                    stat = state.kabutan_package_zip_path.stat()
                    state.kabutan_package_zip_signature = (stat.st_size, stat.st_mtime_ns)
                except OSError:
                    state.kabutan_package_zip_path = None
                    state.kabutan_package_zip_signature = None

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

    def load_watchlist(self, *, watchlist: list[tuple[str, str]], path: Path) -> None:
        self.state.watchlist = watchlist
        self.state.watchlist_path = path
        self.state.controller.save_watchlist_path_cache(path)
        self.state.fundamental_summary_html = ""
        self.state.status = self.state.view_model.build_loaded_status(len(watchlist))
        self.select_first_if_needed()

    def set_kabutan_html_dir(self, path: Path) -> None:
        self.state.kabutan_html_dir = path
        self.state.kabutan_package_zip_path = None
        self.state.kabutan_package_zip_signature = None
        self.state.output_cache.clear()
        self.state.controller.save_kabutan_html_dir_cache(path)
        clear_kabutan_package_zip_cache = getattr(self.state.controller, "clear_kabutan_package_zip_cache", None)
        if callable(clear_kabutan_package_zip_cache):
            clear_kabutan_package_zip_cache()
        self.state.fundamental_summary_html = ""
        self.state.status = self.state.view_model.build_kabutan_dir_selected_status()

    def register_uploaded_kabutan_package(self, zip_path: Path):
        result = self.state.controller.inspect_kabutan_html_package(zip_path=zip_path)
        signature = self.state.controller.build_file_signature(zip_path)
        uploaded_html_dir = self.state.controller.import_output_dir_for_signature(signature) / "html"
        self.state.kabutan_package_zip_path = zip_path
        self.state.kabutan_package_zip_signature = signature
        self.state.kabutan_html_dir = (
            uploaded_html_dir
            if self.state.controller.html_dir_ready(uploaded_html_dir)
            else None
        )
        self.state.output_cache.clear()
        self.state.controller.save_kabutan_package_zip_cache(zip_path)
        if self.state.kabutan_html_dir is not None:
            self.state.controller.save_kabutan_html_dir_cache(self.state.kabutan_html_dir)
        self.state.fundamental_summary_html = ""
        return result

    def ensure_kabutan_html_dir_for_fundamental(self) -> None:
        zip_path = self.state.kabutan_package_zip_path
        if zip_path is None:
            return
        result = self.state.controller.resolve_imported_kabutan_package(
            zip_path=zip_path,
            current_signature=self.state.kabutan_package_zip_signature,
            current_html_dir=self.state.kabutan_html_dir,
        )
        self.state.kabutan_html_dir = result.html_dir
        self.state.kabutan_package_zip_signature = result.signature
        if result.output_cache_should_clear:
            self.state.output_cache.clear()

    def fetch_output_for_current_selection(self) -> bool:
        self.state.fundamental_summary_html = ""
        selected = self.selected_stock()
        if selected is None:
            self.state.status = self.state.view_model.build_missing_stock_status()
            return False
        if self.state.mode != "technical":
            self.ensure_kabutan_html_dir_for_fundamental()
            if self.state.kabutan_html_dir is None:
                self.state.status = self.state.view_model.build_kabutan_dir_restore_required_status()
                return False

        name, code4 = selected
        cache_key = (
            None
            if self.state.mode == "technical"
            else build_output_cache_key(code4, self.state.kabutan_html_dir)
        )
        result = self.state.controller.fetch_output_for_mode(
            name=name,
            code4=code4,
            mode=self.state.mode,
            output_cache=self.state.output_cache,
            output_cache_key=cache_key,
            kabutan_html_dir=self.state.kabutan_html_dir,
        )
        self.state.output = result.output
        self.state.institutional_summary = result.institutional_summary
        self.state.status = self.state.view_model.build_generated_status(name, code4)
        return True

    def build_summary_table_for_current_mode(self):
        if not self.state.watchlist:
            self.state.status = self.state.view_model.build_missing_stock_status()
            self.state.fundamental_summary_html = ""
            return None
        if self.state.mode != "technical":
            self.ensure_kabutan_html_dir_for_fundamental()
            if self.state.kabutan_html_dir is None:
                self.state.status = self.state.view_model.build_kabutan_dir_restore_required_status()
                self.state.fundamental_summary_html = ""
                return None

        return self.state.controller.build_summary_table_for_mode(
            mode=self.state.mode,
            watchlist_entries=self.state.watchlist,
            kabutan_html_dir=self.state.kabutan_html_dir,
        )

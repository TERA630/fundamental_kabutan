"""Web UI state and state management helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from app.gui_view_model import GuiViewModel
from app.services.analysis_application_service import AnalysisApplicationService
from app.ui_state_utils import build_stock_choices, get_selected_stock

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
    selected_label: str = ""
    mode: str = "technical"
    output: str = ""
    institutional_summary: str = DEFAULT_INSTITUTIONAL_SUMMARY
    fundamental_summary_html: str = ""
    summary_kind: str = ""
    summary_markdown: str = ""
    summary_html: str = ""
    summary_filename: str = ""
    technical_evaluation_date: str = ""
    technical_evaluation_time: str = ""
    technical_evaluation_date_choices: list[str] = field(default_factory=list)
    technical_evaluation_time_choices: list[str] = field(default_factory=list)
    technical_evaluation_time_choices_by_date: dict[str, list[str]] = field(default_factory=dict)
    status: str = field(default_factory=GuiViewModel.build_initial_status)
    market_data_operation_lock: Any = field(default_factory=Lock, repr=False)

    @property
    def stock_choices(self) -> list[str]:
        choices, _mapping = build_stock_choices(self.watchlist)
        return choices


class WebUiStateManager:
    def __init__(self, state: WebUiState):
        self.state = state

    def restore_cached_state(self) -> None:
        state = self.state
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

    def sync_form_selection(
        self,
        selected_stock_label: str | None,
        mode: str | None,
        technical_evaluation_date: str | None = None,
        technical_evaluation_time: str | None = None,
    ) -> None:
        if selected_stock_label is not None:
            self.state.selected_label = selected_stock_label
        if mode is not None:
            self.state.mode = mode
        if technical_evaluation_date is not None:
            self.state.technical_evaluation_date = technical_evaluation_date
        if technical_evaluation_time is not None:
            self.state.technical_evaluation_time = technical_evaluation_time

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
        result = self.state.controller.fetch_output_for_mode(
            name=name,
            code4=code4,
            mode=self.state.mode,
            kabutan_html_dir=self.state.kabutan_html_dir,
            evaluation_at=self.technical_evaluation_at(),
        )
        self.state.output = result.output
        self.state.institutional_summary = result.institutional_summary
        status = self.state.view_model.build_generated_status(name, code4)
        if self.state.mode == "technical":
            status = f"{status} / 評価時点={self.technical_evaluation_label()}"
        self.state.status = status
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
            evaluation_at=self.technical_evaluation_at(),
        )

    def technical_evaluation_at(self) -> datetime | None:
        if self.state.mode != "technical":
            return None
        date_text = self.state.technical_evaluation_date.strip()
        time_text = self.state.technical_evaluation_time.strip()
        if not date_text or not time_text:
            return None
        times_by_date = self.state.technical_evaluation_time_choices_by_date
        if times_by_date and time_text not in times_by_date.get(date_text, []):
            return None
        try:
            return datetime.fromisoformat(f"{date_text}T{time_text}")
        except ValueError:
            return None

    def technical_evaluation_label(self) -> str:
        value = self.technical_evaluation_at()
        if value is None:
            return "最新"
        return value.strftime("%Y-%m-%d %H:%M")

    def refresh_technical_evaluation_choices(self) -> None:
        if self.state.mode != "technical":
            return
        selected = self.selected_stock()
        if selected is None:
            self.state.technical_evaluation_date_choices = []
            self.state.technical_evaluation_time_choices = []
            self.state.technical_evaluation_time_choices_by_date = {}
            return
        fetch_timestamps = getattr(self.state.controller, "fetch_technical_evaluation_timestamps", None)
        if not callable(fetch_timestamps):
            return
        try:
            timestamps = fetch_timestamps(selected[1])
        except Exception:
            return
        times_by_date: dict[str, list[str]] = {}
        for value in timestamps:
            date_key = value.date().isoformat()
            times_by_date.setdefault(date_key, []).append(value.strftime("%H:%M"))
        times_by_date = {
            date_key: sorted(set(times))
            for date_key, times in times_by_date.items()
        }
        dates = sorted(times_by_date.keys(), reverse=True)
        selected_date_times = times_by_date.get(self.state.technical_evaluation_date, [])
        times = selected_date_times or sorted({time for values in times_by_date.values() for time in values})
        self.state.technical_evaluation_date_choices = dates
        self.state.technical_evaluation_time_choices = times
        self.state.technical_evaluation_time_choices_by_date = times_by_date
        if self.state.technical_evaluation_date and self.state.technical_evaluation_date not in dates:
            self.state.technical_evaluation_date = ""
            times = sorted({time for values in times_by_date.values() for time in values})
            self.state.technical_evaluation_time_choices = times
        if self.state.technical_evaluation_date:
            valid_times = times_by_date.get(self.state.technical_evaluation_date, [])
        else:
            valid_times = times
        if self.state.technical_evaluation_time and self.state.technical_evaluation_time not in valid_times:
            self.state.technical_evaluation_time = ""

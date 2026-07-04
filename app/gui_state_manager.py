"""State transition helpers for the Tkinter GUI."""

from __future__ import annotations

from datetime import datetime
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
        sector_entries = self._fetch_watchlist_entries_with_sectors(path)
        watchlist = [entry.as_tuple() for entry in sector_entries]
        self.state.watchlist_path = path
        self.controller.save_watchlist_path_cache(path)
        self.state.watchlist = watchlist
        self.state.watchlist_with_sectors = sector_entries
        return self.rebuild_stock_choices()

    def restore_watchlist(self) -> tuple[Path, list[str], str] | None:
        resolved = self.controller.fetch_resolved_watchlist_path()
        if resolved.status != "ok" or resolved.file_path is None:
            return None
        sector_entries = self._fetch_watchlist_entries_with_sectors(resolved.file_path)
        watchlist = [entry.as_tuple() for entry in sector_entries]
        self.state.watchlist_path = resolved.file_path
        self.state.watchlist = watchlist
        self.state.watchlist_with_sectors = sector_entries
        choices = self.rebuild_stock_choices()
        status = self.view_model.build_watchlist_restored_status(len(watchlist))
        return resolved.file_path, choices, status

    def _fetch_watchlist_entries_with_sectors(self, path: Path):
        fetch_with_sectors = getattr(self.controller, "fetch_watchlist_entries_with_sectors", None)
        if callable(fetch_with_sectors):
            return fetch_with_sectors(path)
        from app.domain.models.watchlist import WatchlistEntry

        return [WatchlistEntry(name=name, code4=code4) for name, code4 in self.controller.fetch_watchlist_entries(path)]

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

    def refresh_technical_evaluation_choices(self, selected_label: str) -> None:
        selected = self.selected_stock(selected_label)
        if selected is None:
            self.state.technical_evaluation_date_choices = []
            self.state.technical_evaluation_time_choices = []
            self.state.technical_evaluation_time_choices_by_date = {}
            return
        fetch_timestamps = getattr(self.controller, "fetch_technical_evaluation_timestamps", None)
        if not callable(fetch_timestamps):
            return
        timestamps = fetch_timestamps(selected[1])
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
        valid_times = (
            times_by_date.get(self.state.technical_evaluation_date, [])
            if self.state.technical_evaluation_date
            else times
        )
        if self.state.technical_evaluation_time and self.state.technical_evaluation_time not in valid_times:
            self.state.technical_evaluation_time = ""
            self.state.technical_evaluation_time_is_latest = False

    def set_technical_evaluation_selection(self, *, date_text: str, time_text: str) -> None:
        self.state.technical_evaluation_date = "" if date_text == "最新" else date_text.strip()
        self.state.technical_evaluation_time = "" if time_text == "最新" else time_text.strip()
        self.state.technical_evaluation_time_is_latest = time_text == "最新" or not time_text.strip()

    def update_technical_time_choices_for_selected_date(self) -> None:
        times_by_date = self.state.technical_evaluation_time_choices_by_date
        if self.state.technical_evaluation_date:
            times = times_by_date.get(self.state.technical_evaluation_date, [])
        else:
            times = sorted({time for values in times_by_date.values() for time in values})
        self.state.technical_evaluation_time_choices = times
        if not self.state.technical_evaluation_date:
            return
        if self.state.technical_evaluation_time and self.state.technical_evaluation_time not in times:
            self.state.technical_evaluation_time = ""
        if not self.state.technical_evaluation_time:
            self.state.technical_evaluation_time = self._preferred_historical_time(times)
            self.state.technical_evaluation_time_is_latest = False

    @staticmethod
    def _preferred_historical_time(times: list[str]) -> str:
        """Choose 14:00 when possible, otherwise the nearest usable afternoon bar."""

        if "14:00" in times:
            return "14:00"
        return next((time for time in times if time >= "14:00"), times[-1] if times else "")

    def technical_evaluation_at(self) -> datetime | None:
        date_text = self.state.technical_evaluation_date.strip()
        time_text = self.state.technical_evaluation_time.strip()
        if not date_text:
            return None
        times_by_date = self.state.technical_evaluation_time_choices_by_date
        if not time_text and self.state.technical_evaluation_time_is_latest:
            available_times = times_by_date.get(date_text, [])
            time_text = available_times[-1] if available_times else ""
        if not time_text:
            return None
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

__all__ = ["GuiStateManager"]

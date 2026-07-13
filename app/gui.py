"""GUI layer: Tkinter application wiring and event handling."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from app.gui_state import GuiState
from app.gui_state_manager import GuiStateManager
from app.gui_view import FundamentalView
from app.gui_view_model import GuiViewModel
from app.services.analysis_application_service import AnalysisApplicationService
from app.ui_state_utils import build_default_output_filename


class FundamentalApp:
    """GUI層: 画面イベント連携と状態遷移を担当。"""

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("ファンダメンタル評価 v8（株探/yFinanceベース）")
        self.master.geometry("1040x820")

        self.state = GuiState()
        self.controller = AnalysisApplicationService()
        self.view_model = GuiViewModel()
        self.state_manager = GuiStateManager(
            state=self.state,
            controller=self.controller,
            view_model=self.view_model,
        )

        self.path_var = tk.StringVar(value="監視銘柄ファイル未選択")
        self.kabutan_dir_var = tk.StringVar(value="株探HTMLフォルダ未選択")
        self.stock_var = tk.StringVar()
        self.status_var = tk.StringVar(value=GuiViewModel.build_initial_status())
        self.institutional_summary_var = tk.StringVar(value="機関投資サマリ\n時価総額：N/A\n流動性：N/A\n機関投資スコア：N/A")
        self.technical_evaluation_date_var = tk.StringVar(value="最新")
        self.technical_evaluation_time_var = tk.StringVar(value="最新")

        self.view = FundamentalView(
            self.master,
            self.path_var,
            self.stock_var,
            self.status_var,
            self.kabutan_dir_var,
            self.institutional_summary_var,
            self.technical_evaluation_date_var,
            self.technical_evaluation_time_var,
        )
        self.view.build_ui(
            on_open=self.open_watchlist,
            on_select=self.on_stock_selected,
            on_fetch=self.generate_text,
            on_copy=self.copy_text,
            on_save=self.save_text,
            on_open_kabutan_dir=self.open_kabutan_html_dir,
            on_build_kabutan_package=self.build_kabutan_html_package,
            on_summary=self.generate_summary,
            on_sector_breadth=self.generate_sector_breadth,
            on_tab_changed=self.on_tab_changed,
            on_refresh_technical_evaluation=self.refresh_technical_evaluation_choices,
            on_technical_evaluation_date_changed=self.on_technical_evaluation_date_changed,
        )
        self._apply_technical_evaluation_choices()
        self._restore_watchlist()
        self._restore_kabutan_html_dir()

    def set_busy(self, busy: bool, status: str | None = None):
        self.state.is_fetching = busy
        self.view.set_busy(busy, status)

    def open_watchlist(self):
        path = filedialog.askopenfilename(
            title="監視銘柄ファイルを選択",
            filetypes=[("Markdown/Text", "*.md *.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            choices = self.state_manager.load_watchlist(Path(path))
        except Exception as exc:
            messagebox.showerror("読込失敗", str(exc))
            return

        self.path_var.set(str(self.state.watchlist_path))
        self._apply_stock_choices(choices)

    def _restore_watchlist(self) -> None:
        try:
            restored = self.state_manager.restore_watchlist()
        except Exception:
            return
        if restored is None:
            return
        path, choices, status = restored
        self.path_var.set(str(path))
        self._apply_stock_choices(choices)
        self.status_var.set(status)

    def open_kabutan_html_dir(self):
        path = filedialog.askdirectory(title="株探HTML保存フォルダを選択")
        if not path:
            return
        status = self.state_manager.select_kabutan_html_dir(Path(path))
        self.kabutan_dir_var.set(str(self.state.kabutan_html_dir))
        self.status_var.set(status)

    def _restore_kabutan_html_dir(self) -> None:
        restored = self.state_manager.restore_kabutan_html_dir()
        if restored is None:
            return
        path, status = restored
        self.kabutan_dir_var.set(str(path))
        self.status_var.set(status)

    def _apply_stock_choices(self, choices: list[str]) -> None:
        self.view.set_stock_choices(choices)

        if choices:
            self.stock_var.set(choices[0])
            self.status_var.set(self.view_model.build_loaded_status(len(choices)))
            self.refresh_technical_evaluation_choices()
        else:
            self.stock_var.set("")
            self.view.clear_all_text()
            self.status_var.set(self.view_model.build_no_stock_found_status())

    def on_stock_selected(self, _event=None):
        self.status_var.set(self.view_model.build_selected_status())
        self.refresh_technical_evaluation_choices()

    def on_tab_changed(self, _event=None):
        self.status_var.set(self.view_model.build_selected_status())
        if self.view.current_mode() == "technical":
            self.refresh_technical_evaluation_choices()

    def selected_stock(self) -> tuple[str, str] | None:
        return self.state_manager.selected_stock(self.stock_var.get())

    def _require_selected_stock(self) -> tuple[str, str] | None:
        selected = self.selected_stock()
        if selected is None:
            self.status_var.set(self.view_model.build_missing_stock_status())
            return None
        return selected

    def _render_output(self, output: str, status: str, mode: str | None = None):
        self.view.render_output(output, mode=mode)
        self.set_busy(False, status)

    def _render_output_with_summary(self, output: str, summary: str, status: str, mode: str):
        self.institutional_summary_var.set(summary)
        self._render_output(output, status, mode=mode)

    def _render_appended_output(self, base_output: str, addition: str, status: str, mode: str):
        output = (
            f"{base_output.rstrip()}\n\n{addition.strip()}\n"
            if base_output.strip()
            else addition
        )
        self._render_output(output, status, mode=mode)

    def _sync_technical_evaluation_selection(self) -> None:
        self.state_manager.set_technical_evaluation_selection(
            date_text=self.technical_evaluation_date_var.get(),
            time_text=self.technical_evaluation_time_var.get(),
        )

    def _apply_technical_evaluation_choices(self) -> None:
        date_display = self.state.technical_evaluation_date or "最新"
        time_display = self.state.technical_evaluation_time or "最新"
        self.technical_evaluation_date_var.set(date_display)
        self.technical_evaluation_time_var.set(time_display)
        self.view.set_technical_evaluation_choices(
            dates=self.state.technical_evaluation_date_choices,
            times=self.state.technical_evaluation_time_choices,
        )

    def refresh_technical_evaluation_choices(self) -> None:
        try:
            self._sync_technical_evaluation_selection()
            self.state_manager.refresh_technical_evaluation_choices(self.stock_var.get())
            self._apply_technical_evaluation_choices()
        except Exception as exc:
            self.status_var.set(f"Technical評価時点候補を取得できませんでした: {exc}")

    def on_technical_evaluation_date_changed(self, _event=None) -> None:
        self._sync_technical_evaluation_selection()
        if self.state.technical_evaluation_date:
            self.state_manager.load_technical_times_for_selected_date(self.stock_var.get())
        self.state_manager.update_technical_time_choices_for_selected_date()
        self._apply_technical_evaluation_choices()

    def _handle_fetch_error(self, message: str):
        self.set_busy(False, self.view_model.build_fetch_failed_status())
        messagebox.showerror("取得失敗", message)

    def _handle_summary_error(self, message: str):
        self.set_busy(False, self.view_model.build_summary_failed_status())
        messagebox.showerror("サマリ作成失敗", message)

    def _fetch_worker(self, name: str, code4: str):
        try:
            output = self.controller.fetch_analysis_output(
                name=name,
                code4=code4,
                kabutan_html_dir=self.state.kabutan_html_dir,
            )
            summary = self.controller.fetch_institutional_summary_text(
                name=name,
                code4=code4,
                kabutan_html_dir=self.state.kabutan_html_dir,
            )
            self.master.after(0, lambda: self._render_output_with_summary(output, summary, self.view_model.build_generated_status(name, code4), "fundamental"))
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_fetch_error(msg))

    def _technical_fetch_worker(self, name: str, code4: str, evaluation_at, evaluation_label: str):
        try:
            fetch_technical_output_result = getattr(self.controller, "fetch_technical_output_result", None)
            if callable(fetch_technical_output_result):
                detail = fetch_technical_output_result(name=name, code4=code4, evaluation_at=evaluation_at)
                output = detail.output
            else:
                output = self.controller.fetch_technical_output(name=name, code4=code4, evaluation_at=evaluation_at)
            summary = self.controller.fetch_institutional_summary_text(
                name=name,
                code4=code4,
                kabutan_html_dir=self.state.kabutan_html_dir,
            )
            status = f"{self.view_model.build_generated_status(name, code4)} / 評価時点={evaluation_label}"
            self.master.after(0, lambda: self._render_output_with_summary(output, summary, status, "technical"))
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_fetch_error(msg))

    def _sector_breadth_worker(
        self,
        name: str,
        code4: str,
        evaluation_at,
        evaluation_label: str,
        base_output: str,
    ):
        try:
            if not self.state.sectors_for_code4(code4):
                self.master.after(
                    0,
                    lambda: self.set_busy(False, f"{name}({code4}) は地合評価対象のセクターがありません。"),
                )
                return
            output = self.controller.build_technical_sector_breadth_output(
                watchlist_entries=self.state.technical_watchlist_entries(),
                code4=code4,
                evaluation_at=evaluation_at,
            )
            if not output:
                self.master.after(0, lambda: self.set_busy(False, "地合評価を作成できませんでした。"))
                return
            status = f"地合評価を追加しました。 / 評価時点={evaluation_label}"
            self.master.after(
                0,
                lambda: self._render_appended_output(base_output, output, status, "technical"),
            )
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_fetch_error(msg))

    def _summary_worker(self, output_dir: Path, mode: str, evaluation_at=None, evaluation_label: str = "最新"):
        try:
            if mode == "technical":
                output_path = self.controller.build_and_save_technical_summary(
                    watchlist_entries=self.state.technical_watchlist_entries(),
                    output_dir=output_dir,
                    evaluation_at=evaluation_at,
                )
            else:
                output_path = self.controller.build_and_save_fundamental_summary(
                    watchlist_entries=self.state.watchlist,
                    output_dir=output_dir,
                    kabutan_html_dir=self.state.kabutan_html_dir,
                )
            status = self.view_model.build_saved_status(str(output_path))
            if mode == "technical":
                status = f"{status} / 評価時点={evaluation_label}"
            self.master.after(0, lambda: self.set_busy(False, status))
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_summary_error(msg))

    def _kabutan_package_worker(self, source_dir: Path, output_dir: Path):
        try:
            result = self.controller.build_kabutan_html_package(source_dir=source_dir, output_dir=output_dir)
            self.state.kabutan_html_dir = result.html_dir
            self.controller.save_kabutan_html_dir_cache(result.html_dir)

            def done():
                self.kabutan_dir_var.set(str(result.html_dir))
                self.set_busy(
                    False,
                    (
                        "株探HTMLを正規化してZipを作成しました。"
                        f" 正規化: {result.normalized_count}件 / スキップ: {result.skipped_count}件"
                        f" / zip: {result.zip_path}"
                    ),
                )

            self.master.after(0, done)
        except Exception as exc:
            self.master.after(0, lambda msg=str(exc): self._handle_summary_error(msg))

    def _require_kabutan_html_dir(self) -> bool:
        if self.state.kabutan_html_dir is None:
            self.status_var.set(self.view_model.build_kabutan_dir_restore_required_status())
            self.open_kabutan_html_dir()
            if self.state.kabutan_html_dir is None:
                return False
        return True

    def _start_fetch_thread(self, name: str, code4: str) -> None:
        self.set_busy(True, self.view_model.build_fetching_status(name, code4))
        thread = threading.Thread(target=self._fetch_worker, args=(name, code4), daemon=True)
        thread.start()

    def _start_technical_fetch_thread(self, name: str, code4: str) -> None:
        self._sync_technical_evaluation_selection()
        evaluation_at = self.state_manager.technical_evaluation_at()
        evaluation_label = self.state_manager.technical_evaluation_label()
        self.set_busy(True, self.view_model.build_fetching_status(name, code4))
        thread = threading.Thread(
            target=self._technical_fetch_worker,
            args=(name, code4, evaluation_at, evaluation_label),
            daemon=True,
        )
        thread.start()

    def generate_text(self):
        if self.state.is_fetching:
            return

        selected = self._require_selected_stock()
        if selected is None:
            return

        name, code4 = selected
        if self.view.current_mode() == "technical":
            self._start_technical_fetch_thread(name, code4)
            return

        if not self._require_kabutan_html_dir():
            return

        self._start_fetch_thread(name, code4)

    def generate_summary(self):
        if self.state.is_fetching:
            return

        if not self.state.watchlist:
            self.status_var.set(self.view_model.build_missing_stock_status())
            return

        mode = self.view.current_mode()
        if mode != "technical" and not self._require_kabutan_html_dir():
            return

        output_dir = self.state.watchlist_path.parent if self.state.watchlist_path is not None else Path.cwd()
        self._sync_technical_evaluation_selection()
        evaluation_at = self.state_manager.technical_evaluation_at() if mode == "technical" else None
        evaluation_label = self.state_manager.technical_evaluation_label() if mode == "technical" else "最新"
        self.set_busy(True, self.view_model.build_summary_running_status())
        thread = threading.Thread(
            target=self._summary_worker,
            args=(output_dir, mode, evaluation_at, evaluation_label),
            daemon=True,
        )
        thread.start()

    def generate_sector_breadth(self):
        if self.state.is_fetching:
            return

        selected = self._require_selected_stock()
        if selected is None:
            return

        name, code4 = selected
        self._sync_technical_evaluation_selection()
        evaluation_at = self.state_manager.technical_evaluation_at()
        evaluation_label = self.state_manager.technical_evaluation_label()
        base_output = self.view.text_widget_for_mode("technical").get("1.0", tk.END).strip()
        self.set_busy(True, f"地合評価を作成中... / 評価時点={evaluation_label}")
        thread = threading.Thread(
            target=self._sector_breadth_worker,
            args=(name, code4, evaluation_at, evaluation_label, base_output),
            daemon=True,
        )
        thread.start()

    def build_kabutan_html_package(self):
        if self.state.is_fetching:
            return
        if self.view.current_mode() == "technical":
            return
        if not self._require_kabutan_html_dir():
            return

        source_dir = self.state.kabutan_html_dir
        if source_dir is None:
            return
        output_dir = source_dir.parent / "kabutan_html_package"
        self.set_busy(True, "株探HTMLを正規化してZipを作成中...")
        thread = threading.Thread(target=self._kabutan_package_worker, args=(source_dir, output_dir), daemon=True)
        thread.start()

    def copy_text(self):
        content = self.view.get_text_content()
        if not content:
            self.status_var.set(self.view_model.build_missing_copy_content_status())
            return
        self.master.clipboard_clear()
        self.master.clipboard_append(content)
        self.status_var.set(self.view_model.build_copied_status())

    def save_text(self):
        content = self.view.get_text_content()
        if not content:
            self.status_var.set(self.view_model.build_missing_save_content_status())
            return
        selected = self.selected_stock()
        default_name = build_default_output_filename(selected)
        initial_dir = str(self.state.watchlist_path.parent) if self.state.watchlist_path else str(Path.cwd())
        path = filedialog.asksaveasfilename(
            title="保存先を選択",
            defaultextension=".txt",
            initialdir=initial_dir,
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(content + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("保存失敗", f"ファイルを書き込めませんでした: {exc}")
            self.status_var.set(self.view_model.build_save_failed_status())
            return
        self.status_var.set(self.view_model.build_saved_status(path))


__all__ = ["FundamentalApp"]

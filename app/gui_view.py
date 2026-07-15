"""GUI view: Tkinter widget構築と描画責務。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class FundamentalView:
    """Widget構築と表示更新を担当するView。"""

    def __init__(
        self,
        master: tk.Tk,
        path_var: tk.StringVar,
        stock_var: tk.StringVar,
        status_var: tk.StringVar,
        kabutan_dir_var: tk.StringVar,
        institutional_summary_var: tk.StringVar,
        technical_evaluation_date_var: tk.StringVar,
        technical_evaluation_time_var: tk.StringVar,
    ):
        self.master = master
        self.path_var = path_var
        self.stock_var = stock_var
        self.status_var = status_var
        self.kabutan_dir_var = kabutan_dir_var
        self.institutional_summary_var = institutional_summary_var
        self.technical_evaluation_date_var = technical_evaluation_date_var
        self.technical_evaluation_time_var = technical_evaluation_time_var

    def build_ui(
        self,
        *,
        on_open,
        on_select,
        on_fetch,
        on_manual_technical_quote,
        on_copy,
        on_save,
        on_open_kabutan_dir,
        on_build_kabutan_package,
        on_summary,
        on_sector_breadth,
        on_tab_changed,
        on_refresh_technical_evaluation,
        on_technical_evaluation_date_changed,
    ) -> None:
        root = ttk.Frame(self.master, padding=10)
        root.pack(fill="both", expand=True)

        top = ttk.Frame(root)
        top.pack(fill="x", pady=(0, 8))
        self.open_button = ttk.Button(top, text="監視銘柄ファイルを開く", command=on_open)
        self.open_button.pack(side="left")
        ttk.Label(top, textvariable=self.path_var).pack(side="left", padx=10, fill="x", expand=True)

        kabutan_top = ttk.Frame(root)
        kabutan_top.pack(fill="x", pady=(0, 8))
        self.open_kabutan_dir_button = ttk.Button(kabutan_top, text="株探HTMLフォルダを選択", command=on_open_kabutan_dir)
        self.open_kabutan_dir_button.pack(side="left")
        self.kabutan_package_button = ttk.Button(kabutan_top, text="HTML正規化+Zip作成", command=on_build_kabutan_package)
        self.kabutan_package_button.pack(side="left", padx=(6, 0))
        ttk.Label(kabutan_top, textvariable=self.kabutan_dir_var).pack(side="left", padx=10, fill="x", expand=True)

        control = ttk.Frame(root)
        control.pack(fill="x", pady=(0, 8))
        ttk.Label(control, text="銘柄選択").pack(side="left")
        self.stock_combo = ttk.Combobox(control, textvariable=self.stock_var, state="readonly", width=42)
        self.stock_combo.pack(side="left", padx=(8, 12))
        self.stock_combo.bind("<<ComboboxSelected>>", on_select)
        ttk.Label(control, text="株価: yFinance＋手入力").pack(side="left", padx=(0, 12))
        self.fetch_button = ttk.Button(control, text="取得", command=on_fetch)
        self.fetch_button.pack(side="left", padx=(0, 6))
        self.manual_technical_quote_button = ttk.Button(
            control,
            text="最新値手入力",
            command=on_manual_technical_quote,
        )
        self.manual_technical_quote_button.pack(side="left", padx=(0, 6))
        self.sector_breadth_button = ttk.Button(control, text="地合評価", command=on_sector_breadth)
        self.sector_breadth_button.pack(side="left", padx=(0, 6))
        self.summary_button = ttk.Button(control, text="サマリ出力", command=on_summary)
        self.summary_button.pack(side="left", padx=(0, 6))
        self.copy_button = ttk.Button(control, text="コピー", command=on_copy)
        self.copy_button.pack(side="left", padx=(0, 6))
        self.save_button = ttk.Button(control, text="保存", command=on_save)
        self.save_button.pack(side="left")

        technical_control = ttk.Frame(root)
        technical_control.pack(fill="x", pady=(0, 8))
        ttk.Label(technical_control, text="Technical評価").pack(side="left")
        ttk.Label(technical_control, text="日付").pack(side="left", padx=(10, 4))
        self.technical_evaluation_date_combo = ttk.Combobox(
            technical_control,
            textvariable=self.technical_evaluation_date_var,
            state="readonly",
            width=14,
        )
        self.technical_evaluation_date_combo.pack(side="left", padx=(0, 8))
        self.technical_evaluation_date_combo.bind("<<ComboboxSelected>>", on_technical_evaluation_date_changed)
        ttk.Label(technical_control, text="時刻").pack(side="left", padx=(0, 4))
        self.technical_evaluation_time_combo = ttk.Combobox(
            technical_control,
            textvariable=self.technical_evaluation_time_var,
            state="readonly",
            width=8,
        )
        self.technical_evaluation_time_combo.pack(side="left", padx=(0, 8))
        self.refresh_technical_evaluation_button = ttk.Button(
            technical_control,
            text="候補更新",
            command=on_refresh_technical_evaluation,
        )
        self.refresh_technical_evaluation_button.pack(side="left")
        ttk.Label(technical_control, text="未選択時は最新").pack(side="left", padx=(10, 0))

        ttk.Label(root, textvariable=self.status_var).pack(fill="x", pady=(0, 6))

        summary_frame = ttk.LabelFrame(root, text="機関投資サマリ", padding=8)
        summary_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(summary_frame, textvariable=self.institutional_summary_var, justify="left").pack(fill="x")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

        self.fundamental_frame = ttk.Frame(self.notebook)
        self.technical_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.fundamental_frame, text="Fundamental")
        self.notebook.add(self.technical_frame, text="Technical")

        self.fundamental_text = self._build_text_area(self.fundamental_frame)
        self.technical_text = self._build_text_area(self.technical_frame)
        self.notebook.select(self.technical_frame)

    def _build_text_area(self, parent: ttk.Frame) -> tk.Text:
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill="both", expand=True)
        text = tk.Text(text_frame, wrap="word", font=("Yu Gothic UI", 11))
        text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)
        return text

    def set_stock_choices(self, values: list[str]) -> None:
        self.stock_combo["values"] = values

    def open_manual_technical_quote_dialog(self, stock_label: str, on_apply) -> None:
        dialog = tk.Toplevel(self.master)
        dialog.title("最新値手入力")
        dialog.transient(self.master)
        dialog.resizable(False, False)

        body = ttk.Frame(dialog, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=stock_label, font=("Yu Gothic UI", 11, "bold")).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )

        fields = (
            ("latest", "当日現在値"),
            ("high", "当日高値"),
            ("low", "当日安値"),
            ("vwap", "当日VWAP"),
        )
        variables: dict[str, tk.StringVar] = {}
        first_entry = None
        for row, (key, label) in enumerate(fields, start=1):
            ttk.Label(body, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=4)
            variable = tk.StringVar()
            variables[key] = variable
            entry = ttk.Entry(body, textvariable=variable, width=18, justify="right")
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            if first_entry is None:
                first_entry = entry

        ttk.Label(
            body,
            text="出来高・5分足RSI・前後場VWAPなどはyFinance値を使用します。",
            foreground="#555555",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 4))

        buttons = ttk.Frame(body)
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(8, 0))

        def apply_values(_event=None):
            values = {key: variable.get() for key, variable in variables.items()}
            if on_apply(values, dialog):
                dialog.destroy()

        ttk.Button(buttons, text="キャンセル", command=dialog.destroy).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="反映して再解析", command=apply_values).pack(side="left")
        dialog.bind("<Return>", apply_values)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.grab_set()
        if first_entry is not None:
            first_entry.focus_set()

    def set_busy(self, busy: bool, status: str | None = None) -> None:
        state = "disabled" if busy else "normal"
        readonly_state = "disabled" if busy else "readonly"
        self.open_button.configure(state=state)
        self.open_kabutan_dir_button.configure(state=state)
        self.kabutan_package_button.configure(state=state)
        self.fetch_button.configure(state=state)
        self.manual_technical_quote_button.configure(state=state)
        self.sector_breadth_button.configure(state=state)
        self.summary_button.configure(state=state)
        self.copy_button.configure(state=state)
        self.save_button.configure(state=state)
        self.stock_combo.configure(state=readonly_state)
        self.technical_evaluation_date_combo.configure(state=readonly_state)
        self.technical_evaluation_time_combo.configure(state=readonly_state)
        self.refresh_technical_evaluation_button.configure(state=state)
        if status is not None:
            self.status_var.set(status)
        self.master.update_idletasks()

    def set_technical_evaluation_choices(self, *, dates: list[str], times: list[str]) -> None:
        self.technical_evaluation_date_combo["values"] = ["最新", *dates]
        self.technical_evaluation_time_combo["values"] = ["最新", *times]
        if self.technical_evaluation_date_var.get() not in self.technical_evaluation_date_combo["values"]:
            self.technical_evaluation_date_var.set("最新")
        if self.technical_evaluation_time_var.get() not in self.technical_evaluation_time_combo["values"]:
            self.technical_evaluation_time_var.set("最新")

    def clear_text(self) -> None:
        self.current_text_widget().delete("1.0", tk.END)

    def clear_all_text(self) -> None:
        self.fundamental_text.delete("1.0", tk.END)
        self.technical_text.delete("1.0", tk.END)

    def get_text_content(self) -> str:
        return self.current_text_widget().get("1.0", tk.END).strip()

    def render_output(self, output: str, mode: str | None = None) -> None:
        text = self.text_widget_for_mode(mode or self.current_mode())
        text.delete("1.0", tk.END)
        text.insert("1.0", output)

    def current_mode(self) -> str:
        selected = self.notebook.select()
        if selected == str(self.technical_frame):
            return "technical"
        return "fundamental"

    def current_text_widget(self) -> tk.Text:
        return self.text_widget_for_mode(self.current_mode())

    def text_widget_for_mode(self, mode: str) -> tk.Text:
        return self.technical_text if mode == "technical" else self.fundamental_text


__all__ = ["FundamentalView"]

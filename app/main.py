"""Entry point for the layered application layout."""

from __future__ import annotations

import importlib
import sys
import tkinter as tk


def _ensure_runtime_dependencies() -> None:
    failed: list[tuple[str, str]] = []
    for name in ("pandas",):
        try:
            importlib.import_module(name)
        except Exception as exc:
            failed.append((name, str(exc) or exc.__class__.__name__))
    if not failed:
        return
    details = "\n".join(f"- {name}: {reason}" for name, reason in failed)
    raise RuntimeError(
        "必要なPythonパッケージを読み込めませんでした。\n"
        f"{details}\n"
        f"現在のPython: {sys.executable}\n"
        "このプロジェクトの仮想環境を使うか、依存を入れ直してください:\n"
        r".\.venv\Scripts\python.exe -m app.main"
        "\n"
        "python -m pip install -r requirements.txt"
    )


def main() -> None:
    _ensure_runtime_dependencies()
    from app.gui import FundamentalApp

    root = tk.Tk()
    FundamentalApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

"""Codespaces-friendly launcher for the Flask Web UI."""

from __future__ import annotations

import os

from app.web import create_app

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080


def _get_port() -> int:
    raw_port = os.environ.get("PORT")
    if raw_port is None:
        return DEFAULT_PORT
    try:
        return int(raw_port)
    except ValueError as exc:
        raise SystemExit(f"PORT must be an integer: {raw_port}") from exc


def main() -> None:
    host = os.environ.get("HOST", DEFAULT_HOST)
    port = _get_port()
    print(f"Starting Web UI on {host}:{port}")
    print(f"Codespaces will forward port {port}; local URL: http://localhost:{port}")
    create_app().run(host=host, port=port)


if __name__ == "__main__":
    main()

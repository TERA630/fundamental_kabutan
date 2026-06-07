from pathlib import Path

import pytest

from app.web import WebUiState, build_copy_text, create_app, parse_uploaded_watchlist, resolve_existing_dir


def test_parse_uploaded_watchlist_supports_cp932_bytes():
    data = "トヨタ (7203)\n任天堂,7974\n".encode("cp932")

    entries = parse_uploaded_watchlist(data)

    assert entries == [("トヨタ", "7203"), ("任天堂", "7974")]


def test_build_copy_text_includes_institutional_summary_panel():
    text = build_copy_text("機関投資サマリ\n時価総額：N/A", "本文")

    assert text == "機関投資サマリ\n時価総額：N/A\n\n本文"


def test_resolve_existing_dir_accepts_container_path(tmp_path: Path):
    resolved = resolve_existing_dir(str(tmp_path))

    assert resolved == tmp_path.resolve()


def test_resolve_existing_dir_rejects_missing_path(tmp_path: Path):
    with pytest.raises(ValueError, match="株探HTMLフォルダが見つかりません"):
        resolve_existing_dir(str(tmp_path / "missing"))


def test_index_uses_html_output_panel_without_visible_textarea():
    state = WebUiState()
    state.mode = "fundamental"
    state.output = """■四半期トレンド
　　　売上|営業利益率|昨年同期比|修正一株益
2025.3　10.0億|10.0%|-10%|10.0円
"""
    client = create_app(state).test_client()

    html = client.get("/").data.decode("utf-8")

    assert '<div class="rich-output">' in html
    assert '<table class="fundamental-table">' in html
    assert '<textarea readonly' not in html
    assert '<textarea id="copy-source"' in html


def test_index_renders_technical_output_as_pre_text_not_visible_textarea():
    state = WebUiState()
    state.mode = "technical"
    state.output = "Technical output"
    client = create_app(state).test_client()

    html = client.get("/").data.decode("utf-8")

    assert '<pre class="text-block">Technical output</pre>' in html
    assert '<textarea readonly' not in html

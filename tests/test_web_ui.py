from pathlib import Path

import pytest

from app.web import build_copy_text, parse_uploaded_watchlist, resolve_existing_dir


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

from datetime import date

from app.gui_state import current_date_iso, should_rotate_output_cache


def test_current_date_iso_uses_injected_today() -> None:
    assert current_date_iso(today=date(2026, 5, 26)) == "2026-05-26"


def test_should_rotate_output_cache_when_date_changes() -> None:
    assert should_rotate_output_cache("2026-05-25", today=date(2026, 5, 26)) is True


def test_should_not_rotate_for_same_or_unknown_date() -> None:
    assert should_rotate_output_cache("2026-05-26", today=date(2026, 5, 26)) is False
    assert should_rotate_output_cache(None, today=date(2026, 5, 26)) is False

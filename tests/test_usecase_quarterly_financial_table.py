from app.domain.models.quarterly_financials import Quarter, QuarterlyActual
from app.domain.usecases.quarterly_financial_table import BuildQuarterlyFinancialTableUseCase


def test_execute_selects_latest_five_actual_quarters_only() -> None:
    rows = (
        QuarterlyActual("1234", 2024, Quarter.Q4, 3, 100, 10, 9, 8, 1.0, 9.0),
        QuarterlyActual("1234", 2025, Quarter.Q1, 6, 110, 11, 10, 9, 1.1, 9.1),
        QuarterlyActual("1234", 2025, Quarter.Q2, 9, 120, 12, 11, 10, 1.2, 9.2),
        QuarterlyActual("1234", 2025, Quarter.Q3, 12, 130, 13, 12, 11, 1.3, 9.3),
        QuarterlyActual("1234", 2025, Quarter.Q4, 3, 140, 14, 13, 12, 1.4, 9.4),
        QuarterlyActual("1234", 2026, Quarter.Q1, 6, 150, 15, 14, 13, 1.5, 9.5),
    )
    uc = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3, max_quarters=5)
    out = uc.execute(rows)

    assert len(out) == 5
    assert [(x.fiscal_year, x.quarter_end_month) for x in out] == [
        (2025, 3),
        (2025, 6),
        (2025, 9),
        (2025, 12),
        (2026, 6),
    ]


def test_execute_sets_yoy_na_when_prior_same_quarter_missing() -> None:
    rows = (
        QuarterlyActual("1234", 2025, Quarter.Q1, 6, 110, 11, 10, 9, 1.1, 9.1),
        QuarterlyActual("1234", 2026, Quarter.Q1, 6, 150, 15, 14, 13, 1.5, 9.5),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3, max_quarters=5).execute(rows)

    assert out[0].operating_profit_yoy_pct is None
    assert out[0].revised_eps_yoy_pct is None
    assert out[1].operating_profit_yoy_pct == 40.0


def test_execute_operating_margin_uses_ordinary_profit_when_operating_missing() -> None:
    rows = (
        QuarterlyActual("1234", 2025, Quarter.Q1, 6, 100, 20, None, 18, 1.0, None),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3).execute(rows)
    assert out[0].operating_margin_pct == 20.0


def test_execute_keeps_existing_quarter_when_fiscal_end_month_is_none() -> None:
    rows = (
        QuarterlyActual("1234", 2025, Quarter.Q2, 8, 120, 12, 11, 10, 1.2, None),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=None).execute(rows)
    assert len(out) == 1
    assert out[0].quarter == Quarter.Q2


def test_execute_resolves_non_march_fiscal_cycle_for_yoy_pairing() -> None:
    rows = (
        QuarterlyActual("1234", 2024, None, 12, 100, 10, 10, 9, 1.0, None),
        QuarterlyActual("1234", 2025, None, 12, 150, 15, 15, 14, 1.5, None),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=9).execute(rows)

    assert len(out) == 2
    assert out[0].quarter == Quarter.Q1
    assert out[1].quarter == Quarter.Q1
    assert out[1].operating_profit_yoy_pct == 50.0


def test_execute_sorts_by_month_for_non_march_cycle_latest_slice() -> None:
    rows = (
        QuarterlyActual("1234", 2025, None, 12, 100, 10, 10, 9, 1.0, None),
        QuarterlyActual("1234", 2025, None, 3, 110, 11, 11, 10, 1.1, None),
        QuarterlyActual("1234", 2025, None, 6, 120, 12, 12, 11, 1.2, None),
        QuarterlyActual("1234", 2025, None, 9, 130, 13, 13, 12, 1.3, None),
        QuarterlyActual("1234", 2026, None, 12, 140, 14, 14, 13, 1.4, None),
        QuarterlyActual("1234", 2026, None, 3, 150, 15, 15, 14, 1.5, None),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=9, max_quarters=5).execute(rows)
    assert [(x.fiscal_year, x.quarter_end_month) for x in out] == [
        (2025, 6),
        (2025, 9),
        (2025, 12),
        (2026, 3),
        (2026, 12),
    ]


def test_execute_preserves_final_profit() -> None:
    rows = (
        QuarterlyActual("1234", 2025, Quarter.Q1, 6, 110, 11, 10, 77, 1.1, 9.1),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3, max_quarters=5).execute(rows)
    assert out[0].final_profit == 77


def test_execute_returns_empty_when_rows_empty() -> None:
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3, max_quarters=5).execute(())
    assert out == ()


def test_execute_drops_rows_when_quarter_cannot_be_resolved() -> None:
    rows = (
        QuarterlyActual("1234", 2025, None, None, 100, 10, 9, 8, 1.0, None),
        QuarterlyActual("1234", 2026, None, None, 120, 12, 11, 10, 1.2, None),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3, max_quarters=5).execute(rows)
    assert out == ()


def test_execute_keeps_all_when_less_than_max_quarters() -> None:
    rows = (
        QuarterlyActual("1234", 2025, Quarter.Q1, 3, 100, 10, 9, 8, 1.0, 9.0),
        QuarterlyActual("1234", 2025, Quarter.Q2, 6, 110, 11, 10, 9, 1.1, 9.1),
        QuarterlyActual("1234", 2025, Quarter.Q3, 9, 120, 12, 11, 10, 1.2, 9.2),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3, max_quarters=5).execute(rows)
    assert len(out) == 3
    assert [(x.fiscal_year, x.quarter_end_month) for x in out] == [(2025, 3), (2025, 6), (2025, 9)]

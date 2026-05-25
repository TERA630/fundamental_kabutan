from app.domain.models.quarterly_financials import Quarter, QuarterlyActual
from app.domain.usecases.quarterly_financial_table import BuildQuarterlyFinancialTableUseCase


def test_execute_selects_latest_five_actual_quarters_only() -> None:
    rows = (
        QuarterlyActual("1234", 2024, Quarter.Q4, 3, 100, 10, 9, 1.0, 9.0),
        QuarterlyActual("1234", 2025, Quarter.Q1, 6, 110, 11, 10, 1.1, 9.1),
        QuarterlyActual("1234", 2025, Quarter.Q2, 9, 120, 12, 11, 1.2, 9.2),
        QuarterlyActual("1234", 2025, Quarter.Q3, 12, 130, 13, 12, 1.3, 9.3),
        QuarterlyActual("1234", 2025, Quarter.Q4, 3, 140, 14, 13, 1.4, 9.4),
        QuarterlyActual("1234", 2026, Quarter.Q1, 6, 150, 15, 14, 1.5, 9.5),
    )
    uc = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3, max_quarters=5)
    out = uc.execute(rows)

    assert len(out) == 5
    assert [(x.fiscal_year, x.quarter) for x in out] == [
        (2025, Quarter.Q1),
        (2025, Quarter.Q2),
        (2025, Quarter.Q3),
        (2025, Quarter.Q4),
        (2026, Quarter.Q1),
    ]


def test_execute_sets_yoy_na_when_prior_same_quarter_missing() -> None:
    rows = (
        QuarterlyActual("1234", 2025, Quarter.Q1, 6, 110, 11, 10, 1.1, 9.1),
        QuarterlyActual("1234", 2026, Quarter.Q1, 6, 150, 15, 14, 1.5, 9.5),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3, max_quarters=5).execute(rows)

    assert out[0].operating_profit_yoy_pct is None
    assert out[0].revised_eps_yoy_pct is None
    assert out[1].operating_profit_yoy_pct == 40.0


def test_execute_operating_margin_uses_ordinary_profit_when_operating_missing() -> None:
    rows = (
        QuarterlyActual("1234", 2025, Quarter.Q1, 6, 100, 20, None, 1.0, None),
    )
    out = BuildQuarterlyFinancialTableUseCase(fiscal_end_month=3).execute(rows)
    assert out[0].operating_margin_pct == 20.0

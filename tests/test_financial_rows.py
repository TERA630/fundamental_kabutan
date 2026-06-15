from app.domain.policies.financial_rows import FinancialRowCandidate, select_common_financial_rows


def test_select_common_financial_rows_picks_latest_valid_three_year_window():
    rows = [
        FinancialRowCandidate(2022, 100, 300, 120, 50, 900.0),
        FinancialRowCandidate(2023, 120, 320, 130, 60, 950.0),
        FinancialRowCandidate(2024, 140, 340, 140, 70, 980.0),
        FinancialRowCandidate(2025, None, 360, 150, 80, 1000.0),
    ]

    selected = select_common_financial_rows(rows)

    assert [row.year for row in selected] == [2022, 2023, 2024]


def test_select_common_financial_rows_returns_empty_when_no_common_year_exists():
    rows = [
        FinancialRowCandidate(2023, None, 320, 130, 60, 950.0),
        FinancialRowCandidate(2024, 140, None, 140, 70, 980.0),
    ]

    assert select_common_financial_rows(rows) == []


def test_select_common_financial_rows_skips_invalid_common_year_conditions():
    rows = [
        FinancialRowCandidate(2023, 120, 0, 130, 0, 950.0),
        FinancialRowCandidate(2024, 140, 340, 140, 70, 0.0),
        FinancialRowCandidate(2025, 150, 360, 150, 80, 1000.0),
    ]

    selected = select_common_financial_rows(rows)

    assert [row.year for row in selected] == [2025]

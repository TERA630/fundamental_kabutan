import unittest
from app.domain.models.periods import fetch_period_set


class TestPeriodMerge(unittest.TestCase):
    def test_prev_fy_is_merged_when_revision_row_has_blanks(self):
        rows = [
            {"Code": "80580", "CurPerType": "FY", "CurPerSt": "2023-04-01", "CurPerEn": "2024-03-31", "DisclosedDate": "2024-05-08", "Sales": "1000", "OP": "100", "OdP": "90", "NP": "60", "EPS": "50"},
            {"Code": "80580", "CurPerType": "FY", "CurPerSt": "2023-04-01", "CurPerEn": "2024-03-31", "DisclosedDate": "2024-06-01", "Sales": "", "OP": None, "OdP": "", "NP": "", "EPS": ""},
            {"Code": "80580", "CurPerType": "FY", "CurPerSt": "2024-04-01", "CurPerEn": "2025-03-31", "DisclosedDate": "2025-05-08", "Sales": "1100", "OP": "120", "OdP": "100", "NP": "70", "EPS": "55"},
        ]

        periods = fetch_period_set(rows)

        self.assertIsNotNone(periods.latest_fy)
        self.assertIsNotNone(periods.prev_fy)
        self.assertEqual(periods.latest_fy.fiscal_year, 2024)
        self.assertEqual(periods.prev_fy.fiscal_year, 2023)
        self.assertEqual(periods.prev_fy.row.get("Sales"), "1000")
        self.assertEqual(periods.prev_fy.row.get("OP"), "100")
        self.assertEqual(periods.prev_fy.row.get("OdP"), "90")
        self.assertEqual(periods.prev_fy.row.get("NP"), "60")
        self.assertEqual(periods.prev_fy.row.get("EPS"), "50")


if __name__ == "__main__":
    unittest.main()

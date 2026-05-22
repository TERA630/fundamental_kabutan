from datetime import date

import pytest

from app.domain.models.fundamental_display import PeriodFundamentalRow, PriceSnapshot, StockProfile, ValuationMetrics
from app.domain.usecases.fundamental_display import (
    BuildFundamentalDisplaySnapshotUseCase,
    calc_dividend_yield_pct,
    calc_operating_growth_yoy_pct,
    calc_operating_margin_pct,
    calc_per_times,
    calc_ordinary_margin_pct,
    grade_company_scale,
)


class _FundamentalRepo:
    def fetch_stock_profile(self, code4: str) -> StockProfile:
        return StockProfile(code4=code4, name="テスト", industry_name="情報・通信", market_cap_billion_yen=3500, size_class_label=None)

    def fetch_fundamental_rows(self, code4: str, years: tuple[int, ...]) -> list[PeriodFundamentalRow]:
        return [
            PeriodFundamentalRow("actual", years[0], 100, 10, 8, 6, 60, 20),
            PeriodFundamentalRow("actual", years[1], 120, 12, 9, 7, 70, 22),
            PeriodFundamentalRow("actual", years[2], 130, 13, 10, 8, 80, 24),
            PeriodFundamentalRow("forecast", years[3], 150, 15, 12, 9, 90, 26),
            PeriodFundamentalRow("forecast", years[4], 160, 16, 13, 10, 100, 28),
        ]


class _MarketRepo:
    def fetch_price_snapshot(self, code4: str) -> PriceSnapshot:
        return PriceSnapshot(price_yen=1234.0, as_of_date=date(2026, 5, 22))


class _ValuationRepo:
    def fetch_valuation_metrics(self, code4: str, fiscal_year: int, kind: str) -> ValuationMetrics:
        return ValuationMetrics(per=10.0 + (fiscal_year % 3), eps_yen=100.0, dividend_yield_pct=2.0)


def test_calc_metrics_functions():
    prev = PeriodFundamentalRow("actual", 2024, 100, 10, 8, 6, 60, 20)
    curr = PeriodFundamentalRow("actual", 2025, 120, 12, 9, 7, 70, 22)
    assert calc_operating_margin_pct(curr) == 10
    assert calc_ordinary_margin_pct(curr) == 7.5
    assert calc_operating_growth_yoy_pct(curr, prev) == pytest.approx(20.0)
    assert calc_per_times(1200, 80) == pytest.approx(15.0)
    assert calc_dividend_yield_pct(1200, 24) == pytest.approx(2.0)


def test_grade_company_scale():
    assert grade_company_scale(3500) == "中型主役"


def test_get_fundamental_display_snapshot_builds_filled_rows():
    usecase = BuildFundamentalDisplaySnapshotUseCase(
        fundamental_repository=_FundamentalRepo(),
        market_repository=_MarketRepo(),
        valuation_repository=_ValuationRepo(),
    )
    snapshot = usecase.get_fundamental_display_snapshot("1234", base_year=2025)

    assert snapshot.profile.size_class_label == "中型主役"
    assert snapshot.price.price_yen == 1234.0
    assert len(snapshot.rows) == 5
    assert snapshot.rows[0].operating_growth_yoy_pct is None
    assert snapshot.rows[1].operating_growth_yoy_pct == pytest.approx(20.0)
    assert snapshot.metrics_actual is not None
    assert snapshot.metrics_actual.per == pytest.approx(1234.0 / 80)
    assert snapshot.metrics_actual.dividend_yield_pct == pytest.approx(24 / 1234.0 * 100)
    assert snapshot.metrics_current_forecast is not None
    assert snapshot.metrics_current_forecast.per == pytest.approx(1234.0 / 90)

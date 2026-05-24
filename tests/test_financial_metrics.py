from app.domain.policies.financial_metrics import (
    DEFAULT_EFFECTIVE_TAX_RATE,
    calc_pbr,
    calc_roe,
    calc_roic_approx,
)


def test_calc_roe_formula():
    assert calc_roe(120, 600) == 20.0


def test_calc_roe_returns_none_on_invalid_denominator():
    assert calc_roe(120, 0) is None
    assert calc_roe(120, None) is None


def test_calc_pbr_formula():
    assert calc_pbr(3000, 1500) == 2.0


def test_calc_pbr_returns_none_on_invalid_denominator():
    assert calc_pbr(3000, 0) is None
    assert calc_pbr(3000, None) is None


def test_calc_roic_approx_formula_with_default_tax_rate():
    # NOPAT = 100 * (1 - 0.30) = 70, invested capital = 600 + 100 = 700
    assert calc_roic_approx(100, 600, 100) == 10.0


def test_calc_roic_approx_returns_none_when_inputs_are_missing_or_invested_capital_zero():
    assert calc_roic_approx(None, 600, 100) is None
    assert calc_roic_approx(100, None, 100) is None
    assert calc_roic_approx(100, 600, None) is None
    assert calc_roic_approx(100, -100, 100) is None


def test_default_effective_tax_rate_is_fixed_30_percent():
    assert DEFAULT_EFFECTIVE_TAX_RATE == 0.30

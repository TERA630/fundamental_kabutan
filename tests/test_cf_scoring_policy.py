from app.domain.models.cf_scoring_input import CfScoringInput
from app.domain.policies.cf_scoring import calculate_cf_score, score_per


def test_calculate_cf_score_high_case_reaches_100_and_top_judgement():
    data = CfScoringInput(
        code4="1234",
        as_of="2026-05-26",
        roic=30.0,
        ocf=200.0,
        net_income=100.0,
        operating_income=120.0,
        revenue=800.0,
        fcf=150.0,
        eps_cagr_3y=30.0,
        sales_cagr_3y=25.0,
        fcf_yield=8.0,
        per=14.0,
    )
    result = calculate_cf_score(data)
    assert result.total.total_points == 98
    assert result.total.judgement == "S"
    assert result.total.investment_category == "機関主導グロース候補"


def test_quality_filter_caps_cash_conversion_to_c_when_ocf_op_is_low():
    data = CfScoringInput(
        code4="1234",
        as_of=None,
        roic=20.0,
        ocf=130.0,
        net_income=100.0,
        operating_income=300.0,
        revenue=1000.0,
        fcf=200.0,
        eps_cagr_3y=10.0,
        sales_cagr_3y=10.0,
        fcf_yield=3.0,
        per=20.0,
    )
    result = calculate_cf_score(data)
    metric = next(m for m in result.quality.metrics if m.metric_id == "cash_conversion_np")
    assert metric.rank == "C"
    assert metric.points == 5
    assert any("capped" in note for note in metric.rule_notes)


def test_fcf_ratio_growth_exemption_promotes_to_a7():
    data = CfScoringInput(
        code4="1234",
        as_of=None,
        roic=16.0,
        ocf=100.0,
        net_income=80.0,
        operating_income=90.0,
        revenue=500.0,
        fcf=20.0,
        eps_cagr_3y=16.0,
        sales_cagr_3y=16.0,
        fcf_yield=2.0,
        per=30.0,
    )
    result = calculate_cf_score(data)
    metric = next(m for m in result.quality.metrics if m.metric_id == "fcf_ratio")
    assert metric.rank == "A"
    assert metric.points == 7


def test_fcf_yield_growth_floor_raises_d_to_c2():
    data = CfScoringInput(
        code4="1234",
        as_of=None,
        roic=10.0,
        ocf=100.0,
        net_income=100.0,
        operating_income=100.0,
        revenue=1000.0,
        fcf=40.0,
        eps_cagr_3y=10.0,
        sales_cagr_3y=16.0,
        fcf_yield=0.5,
        per=30.0,
    )
    result = calculate_cf_score(data)
    metric = next(m for m in result.valuation.metrics if m.metric_id == "fcf_yield")
    assert metric.rank == "C"
    assert metric.points == 2


def test_per_high_growth_bonus_for_c_and_d_ranges():
    c_metric = score_per(40.0, 25.0)
    d_metric = score_per(55.0, 25.0)
    assert c_metric.points == 2
    assert d_metric.points == 1


def test_total_judgement_boundaries():
    # Build with many missing values to drop score below thresholds
    data = CfScoringInput(
        code4="1234",
        as_of=None,
        roic=None,
        ocf=None,
        net_income=None,
        operating_income=None,
        revenue=None,
        fcf=None,
        eps_cagr_3y=None,
        sales_cagr_3y=None,
        fcf_yield=None,
        per=None,
    )
    result = calculate_cf_score(data)
    assert result.total.total_points == 0
    assert result.total.judgement == "C"
    assert result.total.investment_category == "対象外"


def test_total_judgement_grade_boundaries_are_s_a_b_c():
    s_case = CfScoringInput("1111", None, 30.0, 200.0, 100.0, 120.0, 800.0, 150.0, 30.0, 25.0, 8.0, 14.0)
    a_case = CfScoringInput("1111", None, 20.0, 120.0, 100.0, 100.0, 1000.0, 60.0, 15.0, 12.0, 2.0, 20.0)
    b_case = CfScoringInput("1111", None, 10.0, 100.0, 100.0, 80.0, 1000.0, 10.0, 5.0, 5.0, 2.0, 30.0)
    c_case = CfScoringInput("1111", None, None, None, None, None, None, None, None, None, None, None)

    assert calculate_cf_score(s_case).total.judgement == "S"
    assert calculate_cf_score(a_case).total.judgement == "A"
    assert calculate_cf_score(b_case).total.judgement == "B"
    assert calculate_cf_score(c_case).total.judgement == "C"


def test_score_per_negative_or_zero_is_not_scored_as_s():
    neg = score_per(-12.0, 30.0)
    zero = score_per(0.0, 30.0)
    assert neg.rank == "D"
    assert neg.points == 0
    assert zero.rank == "D"
    assert zero.points == 0


def test_cash_conversion_negative_signs_do_not_get_high_scores():
    both_negative = CfScoringInput(
        code4="9999",
        as_of=None,
        roic=10.0,
        ocf=-100.0,
        net_income=-50.0,
        operating_income=80.0,
        revenue=1000.0,
        fcf=10.0,
        eps_cagr_3y=5.0,
        sales_cagr_3y=5.0,
        fcf_yield=2.0,
        per=20.0,
    )
    result = calculate_cf_score(both_negative)
    metric = next(m for m in result.quality.metrics if m.metric_id == "cash_conversion_np")
    assert metric.rank == "E"
    assert metric.points == 0


def test_cash_conversion_non_positive_ocf_is_e0_even_with_positive_income():
    data = CfScoringInput(
        code4="9999",
        as_of=None,
        roic=10.0,
        ocf=0.0,
        net_income=100.0,
        operating_income=80.0,
        revenue=1000.0,
        fcf=10.0,
        eps_cagr_3y=5.0,
        sales_cagr_3y=5.0,
        fcf_yield=2.0,
        per=20.0,
    )
    result = calculate_cf_score(data)
    metric = next(m for m in result.quality.metrics if m.metric_id == "cash_conversion_np")
    assert metric.rank == "E"
    assert metric.points == 0


def test_fcf_ratio_non_positive_ocf_is_not_scored_as_s():
    data = CfScoringInput(
        code4="7777",
        as_of=None,
        roic=18.0,
        ocf=-100.0,
        net_income=100.0,
        operating_income=90.0,
        revenue=1000.0,
        fcf=-80.0,
        eps_cagr_3y=12.0,
        sales_cagr_3y=12.0,
        fcf_yield=3.0,
        per=25.0,
    )
    result = calculate_cf_score(data)
    metric = next(m for m in result.quality.metrics if m.metric_id == "fcf_ratio")
    assert metric.rank == "C"
    assert metric.points == 0


def test_fcf_ratio_negative_fcf_still_gets_growth_exemption_when_conditions_match():
    data = CfScoringInput(
        code4="7777",
        as_of=None,
        roic=18.0,
        ocf=100.0,
        net_income=100.0,
        operating_income=90.0,
        revenue=1000.0,
        fcf=-10.0,
        eps_cagr_3y=12.0,
        sales_cagr_3y=16.0,
        fcf_yield=3.0,
        per=25.0,
    )
    result = calculate_cf_score(data)
    metric = next(m for m in result.quality.metrics if m.metric_id == "fcf_ratio")
    assert metric.rank == "A"
    assert metric.points == 7
    assert any("growth_exemption" in note for note in metric.rule_notes)


def test_fcf_ratio_zero_ocf_is_explicit_invalid_c0_not_na():
    data = CfScoringInput(
        code4="7777",
        as_of=None,
        roic=18.0,
        ocf=0.0,
        net_income=100.0,
        operating_income=90.0,
        revenue=1000.0,
        fcf=20.0,
        eps_cagr_3y=12.0,
        sales_cagr_3y=12.0,
        fcf_yield=3.0,
        per=25.0,
    )
    result = calculate_cf_score(data)
    metric = next(m for m in result.quality.metrics if m.metric_id == "fcf_ratio")
    assert metric.rank == "C"
    assert metric.points == 0
    assert any("ocf == 0" in note for note in metric.rule_notes)


def test_fcf_ratio_none_ocf_is_na():
    data = CfScoringInput(
        code4="7777",
        as_of=None,
        roic=18.0,
        ocf=None,
        net_income=100.0,
        operating_income=90.0,
        revenue=1000.0,
        fcf=20.0,
        eps_cagr_3y=12.0,
        sales_cagr_3y=12.0,
        fcf_yield=3.0,
        per=25.0,
    )
    result = calculate_cf_score(data)
    metric = next(m for m in result.quality.metrics if m.metric_id == "fcf_ratio")
    assert metric.rank == "N/A"
    assert metric.points == 0

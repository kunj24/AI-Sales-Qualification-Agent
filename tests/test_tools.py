from tools import check_budget_eligibility


def test_budget_meets_minimum():
    result = check_budget_eligibility(80000, 50000)
    assert result.success is True
    assert result.eligible is True


def test_budget_below_minimum():
    result = check_budget_eligibility(20000, 50000)
    assert result.success is True
    assert result.eligible is False


def test_missing_budget_is_unknown_not_ineligible():
    result = check_budget_eligibility(None, 50000)
    assert result.success is True
    assert result.eligible is None


def test_negative_budget_returns_controlled_error():
    result = check_budget_eligibility(-1, 50000)
    assert result.success is False
    assert result.error_code == "INVALID_BUDGET"


def test_invalid_minimum_returns_controlled_error():
    result = check_budget_eligibility(80000, -1)
    assert result.success is False
    assert result.error_code == "INVALID_MINIMUM_BUDGET"

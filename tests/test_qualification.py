from qualification import QualificationConfig, qualify_lead
from schemas import Budget, ContactDetails, LeadRecord, LeadStatus
from tools import ToolResult


def complete_lead(**overrides):
    data = dict(
        customer_name="Asha Patel",
        contact_details=ContactDetails(email="asha@example.com"),
        requirements=["E-commerce website"],
        budget=Budget(amount=80000, currency="INR"),
        timeline="Within 2 months",
    )
    data.update(overrides)
    return LeadRecord(**data)


def test_complete_lead_with_eligible_budget_is_qualified():
    result = qualify_lead(complete_lead())
    assert result.lead_status == LeadStatus.QUALIFIED
    assert result.tool_result["eligible"] is True


def test_missing_contact_means_more_information():
    lead = complete_lead(contact_details=ContactDetails())
    result = qualify_lead(lead)
    assert result.lead_status == LeadStatus.NEEDS_MORE_INFORMATION
    assert "At least one contact method (email or phone)" in result.missing_information


def test_missing_budget_means_more_information():
    lead = complete_lead(budget=Budget())
    result = qualify_lead(lead)
    assert result.lead_status == LeadStatus.NEEDS_MORE_INFORMATION
    assert "Budget" in result.missing_information


def test_contradiction_means_more_information():
    lead = complete_lead(contradictions=["Customer gave two different budgets"])
    result = qualify_lead(lead)
    assert result.lead_status == LeadStatus.NEEDS_MORE_INFORMATION
    assert "Clarification of contradictory information" in result.missing_information


def test_complete_lead_below_threshold_is_unqualified():
    lead = complete_lead(budget=Budget(amount=20000))
    result = qualify_lead(lead, QualificationConfig(minimum_budget=50000))
    assert result.lead_status == LeadStatus.UNQUALIFIED
    assert result.tool_result["eligible"] is False


def test_tool_failure_never_qualifies_lead():
    failed = ToolResult(
        tool_name="budget_eligibility", success=False, eligible=None,
        budget=80000, minimum_budget=50000,
        reason="Tool unavailable", error_code="TOOL_UNAVAILABLE"
    )
    result = qualify_lead(complete_lead(), tool_result=failed)
    assert result.lead_status == LeadStatus.NEEDS_MORE_INFORMATION
    assert "could not be completed" in result.reason


def test_changed_configuration_changes_decision():
    lead = complete_lead()
    low_threshold = qualify_lead(lead, QualificationConfig(minimum_budget=50000))
    high_threshold = qualify_lead(lead, QualificationConfig(minimum_budget=100000))
    assert low_threshold.lead_status == LeadStatus.QUALIFIED
    assert high_threshold.lead_status == LeadStatus.UNQUALIFIED


def test_requirements_can_be_configured_as_optional():
    lead = complete_lead(requirements=[])
    result = qualify_lead(lead, QualificationConfig(require_requirements=False))
    assert result.lead_status == LeadStatus.QUALIFIED

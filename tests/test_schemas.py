import pytest
from pydantic import ValidationError

from schemas import Budget, LeadRecord, LeadStatus


def test_lead_defaults_to_needs_more_information():
    lead = LeadRecord()
    assert lead.lead_status == LeadStatus.NEEDS_MORE_INFORMATION
    assert lead.budget.amount is None


def test_lead_serializes_to_valid_json():
    lead = LeadRecord(
        customer_name="Asha",
        requirements=["E-commerce website"],
        budget=Budget(amount=80000, currency="INR"),
        timeline="Within 2 months",
    )
    parsed = LeadRecord.model_validate_json(lead.model_dump_json())
    assert parsed.customer_name == "Asha"


def test_negative_budget_is_rejected():
    with pytest.raises(ValidationError):
        Budget(amount=-10)


def test_invalid_status_is_rejected():
    with pytest.raises(ValidationError):
        LeadRecord(lead_status="Maybe Qualified")


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        LeadRecord(unexpected_secret="value")

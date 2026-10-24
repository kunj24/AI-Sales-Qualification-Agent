from qualification import qualify_lead
from schemas import Budget, ContactDetails, LeadRecord, LeadStatus


def test_newly_filled_fields_clear_stale_missing_information():
    lead = LeadRecord(
        contact_details=ContactDetails(email="lead@example.com"),
        requirements=["CRM"],
        budget=Budget(amount=70000),
        timeline="Next quarter",
        missing_information=["Budget", "Project requirements"],
    )
    result = qualify_lead(lead)
    assert result.lead_status == LeadStatus.QUALIFIED
    assert result.missing_information == []

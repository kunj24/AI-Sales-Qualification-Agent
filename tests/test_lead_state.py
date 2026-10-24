from lead_state import merge_extraction_into_lead
from schemas import Budget, ContactDetails, LeadExtraction, LeadRecord


def test_merge_adds_new_facts_without_erasing_old_facts():
    existing = LeadRecord(
        customer_name="Asha Patel",
        contact_details=ContactDetails(email="asha@example.com"),
        requirements=["Website"],
        budget=Budget(amount=80000, currency="INR"),
        timeline="Within two months",
    )
    extraction = LeadExtraction(phone="9876543210", requirements=["Payment integration"])
    merged = merge_extraction_into_lead(existing, extraction)
    assert merged.customer_name == "Asha Patel"
    assert merged.contact_details.email == "asha@example.com"
    assert merged.contact_details.phone == "9876543210"
    assert merged.requirements == ["Website", "Payment integration"]
    assert merged.budget.amount == 80000
    assert merged.timeline == "Within two months"


def test_merge_replaces_resolved_contradictions_and_clears_stale_missing_list():
    existing = LeadRecord(contradictions=["Two different budgets"], missing_information=["Budget"])
    extraction = LeadExtraction(budget_amount=75000, contradictions=[])
    merged = merge_extraction_into_lead(existing, extraction)
    assert merged.contradictions == []
    assert merged.missing_information == []
    assert merged.budget.amount == 75000

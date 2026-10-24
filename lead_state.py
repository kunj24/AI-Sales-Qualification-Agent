"""Pure helpers for merging extracted facts into the current lead record."""
from __future__ import annotations

from schemas import Budget, ContactDetails, LeadExtraction, LeadRecord


def merge_extraction_into_lead(existing: LeadRecord, extraction: LeadExtraction) -> LeadRecord:
    """Merge new facts without erasing previously captured facts with null/empty values.

    Contradictions are replaced because extraction is based on the complete conversation;
    this lets a customer's later clarification resolve an earlier contradiction.
    """
    data = existing.model_dump()

    if extraction.customer_name:
        data["customer_name"] = extraction.customer_name

    contact = data.get("contact_details") or {}
    if extraction.email:
        contact["email"] = extraction.email
    if extraction.phone:
        contact["phone"] = extraction.phone
    data["contact_details"] = contact

    if extraction.requirements:
        # Keep distinct requirements gathered across turns.
        data["requirements"] = list(dict.fromkeys(data.get("requirements", []) + extraction.requirements))

    if extraction.budget_amount is not None:
        data["budget"] = {"amount": extraction.budget_amount, "currency": extraction.budget_currency or "INR"}
    elif not data.get("budget"):
        data["budget"] = Budget().model_dump()

    if extraction.timeline:
        data["timeline"] = extraction.timeline

    data["contradictions"] = extraction.contradictions
    # Recomputed by the deterministic qualification engine, not kept stale from prior turns.
    data["missing_information"] = []
    return LeadRecord.model_validate(data)

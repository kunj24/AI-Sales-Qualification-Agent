"""Deterministic lead qualification rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from schemas import LeadRecord, LeadStatus
from tools import ToolResult, check_budget_eligibility


@dataclass(frozen=True)
class QualificationConfig:
    minimum_budget: float = 50_000
    require_contact_method: bool = True
    require_timeline: bool = True
    require_requirements: bool = True


def qualify_lead(
    lead: LeadRecord,
    config: QualificationConfig = QualificationConfig(),
    tool_result: Optional[ToolResult] = None,
) -> LeadRecord:
    """
    Evaluate a lead in a deterministic order:
    contradictions -> missing required data -> tool failure -> business decision.
    """
    result = lead.model_copy(deep=True)

    if result.contradictions:
        result.lead_status = LeadStatus.NEEDS_MORE_INFORMATION
        result.missing_information = list(dict.fromkeys(
            result.missing_information + ["Clarification of contradictory information"]
        ))
        result.reason = (
            "The lead cannot be evaluated until these contradictions are resolved: "
            + "; ".join(result.contradictions)
        )
        result.tool_result = tool_result.to_dict() if tool_result else None
        return result

    # Missing fields are recomputed on every turn so newly supplied information clears old gaps.
    missing = []

    if config.require_requirements and not result.requirements:
        missing.append("Project requirements")
    if result.budget.amount is None:
        missing.append("Budget")
    if config.require_timeline and not result.timeline:
        missing.append("Timeline")
    if config.require_contact_method:
        contact = result.contact_details
        if not contact.email and not contact.phone:
            missing.append("At least one contact method (email or phone)")

    # Preserve order while removing duplicate missing fields.
    result.missing_information = list(dict.fromkeys(missing))

    if result.missing_information:
        result.lead_status = LeadStatus.NEEDS_MORE_INFORMATION
        result.reason = (
            "Required qualification information is missing: "
            + ", ".join(result.missing_information)
        )
        result.tool_result = tool_result.to_dict() if tool_result else None
        return result

    actual_tool_result = tool_result or check_budget_eligibility(
        result.budget.amount, config.minimum_budget
    )
    result.tool_result = actual_tool_result.to_dict()

    if not actual_tool_result.success or actual_tool_result.eligible is None:
        result.lead_status = LeadStatus.NEEDS_MORE_INFORMATION
        result.reason = (
            "Qualification could not be completed because the eligibility tool "
            "did not return a usable result. Please retry or review the tool error."
        )
        return result

    if actual_tool_result.eligible:
        result.lead_status = LeadStatus.QUALIFIED
        result.reason = (
            "All configured required fields are present and the eligibility tool "
            "confirmed that the stated budget meets the configured minimum."
        )
    else:
        result.lead_status = LeadStatus.UNQUALIFIED
        result.reason = (
            "Required lead information is present, but the eligibility tool "
            "confirmed that the stated budget is below the configured minimum."
        )

    result.missing_information = []
    return result

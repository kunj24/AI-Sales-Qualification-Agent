"""Deterministic business tools. No LLM or network call is made here."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    success: bool
    eligible: Optional[bool]
    budget: Optional[float]
    minimum_budget: float
    reason: str
    error_code: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def check_budget_eligibility(
    budget: Optional[float],
    minimum_budget: float = 50_000,
) -> ToolResult:
    """
    Compare a known customer budget with the configured minimum.

    A missing budget is not treated as zero or as a negative eligibility result.
    Invalid arguments return a controlled failure rather than raising an exception.
    """
    if isinstance(minimum_budget, bool) or not isinstance(minimum_budget, (int, float)):
        return ToolResult(
            "budget_eligibility", False, None, None, 0,
            "Minimum budget must be a number.", "INVALID_MINIMUM_BUDGET"
        )
    if minimum_budget < 0:
        return ToolResult(
            "budget_eligibility", False, None, None, float(minimum_budget),
            "Minimum budget cannot be negative.", "INVALID_MINIMUM_BUDGET"
        )

    if budget is None:
        return ToolResult(
            "budget_eligibility", True, None, None, float(minimum_budget),
            "Budget was not provided; eligibility cannot yet be evaluated."
        )

    if isinstance(budget, bool) or not isinstance(budget, (int, float)):
        return ToolResult(
            "budget_eligibility", False, None, None, float(minimum_budget),
            "Budget must be a number.", "INVALID_BUDGET"
        )
    if budget < 0:
        return ToolResult(
            "budget_eligibility", False, None, float(budget), float(minimum_budget),
            "Budget cannot be negative.", "INVALID_BUDGET"
        )

    eligible = float(budget) >= float(minimum_budget)
    reason = (
        "The stated budget meets the configured minimum."
        if eligible
        else "The stated budget is below the configured minimum."
    )
    return ToolResult(
        "budget_eligibility", True, eligible, float(budget),
        float(minimum_budget), reason
    )

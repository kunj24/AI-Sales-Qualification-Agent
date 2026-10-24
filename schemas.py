"""Validated data models for the AI Sales Qualification Agent."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadStatus(str, Enum):
    QUALIFIED = "Qualified"
    UNQUALIFIED = "Unqualified"
    NEEDS_MORE_INFORMATION = "Needs More Information"


class ContactDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("email", "phone")
    @classmethod
    def blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            return None
        return value.strip() if value is not None else None


class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Optional[float] = Field(default=None, ge=0)
    currency: str = "INR"

    @field_validator("currency")
    @classmethod
    def currency_must_be_present(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("currency cannot be blank")
        return cleaned


class LeadRecord(BaseModel):
    """The final structured lead record required by the assignment."""
    model_config = ConfigDict(extra="forbid")

    customer_name: Optional[str] = None
    contact_details: ContactDetails = Field(default_factory=ContactDetails)
    requirements: list[str] = Field(default_factory=list)
    budget: Budget = Field(default_factory=Budget)
    timeline: Optional[str] = None
    lead_status: LeadStatus = LeadStatus.NEEDS_MORE_INFORMATION
    missing_information: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    reason: str = "Not yet evaluated"
    tool_result: Optional[dict] = None

    @field_validator("customer_name", "timeline")
    @classmethod
    def blank_strings_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            return None
        return value.strip() if value is not None else None

    @field_validator("requirements", "missing_information", "contradictions")
    @classmethod
    def strip_list_values(cls, values: list[str]) -> list[str]:
        return [item.strip() for item in values if item and item.strip()]


class LeadExtraction(BaseModel):
    """Facts extracted from conversation; this model does not decide qualification."""
    model_config = ConfigDict(extra="forbid")

    intent: str = "Unknown"
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    requirements: list[str] = Field(default_factory=list)
    budget_amount: Optional[float] = Field(default=None, ge=0)
    budget_currency: str = "INR"
    timeline: Optional[str] = None
    contradictions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    follow_up_question: Optional[str] = None
    customer_reply: str = "Could you tell me a little more about your requirements?"

    @field_validator(
        "intent", "customer_name", "email", "phone", "budget_currency",
        "timeline", "follow_up_question", "customer_reply"
    )
    @classmethod
    def clean_optional_text(cls, value):
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned

"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from enum import Enum
from pydantic import field_validator, model_validator

from app.schemas.validators import (
    validate_date_ymd,
    validate_description,
    validate_name_field,
    validate_optional_str,
    validate_positive_number,
)
from app.schemas.base_schema import BaseSchema, TimestampSchema

# ============================================
# Reimbursement Schemas
# ============================================

class ReimbursementStatus(str, Enum):
    """Reimbursement status enum."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class ReimbursementItemBase(BaseSchema):
    """Base reimbursement item schema."""
    category_id: UUID
    expense_date: date
    description: str
    amount: float
    quantity: float = 1
    unit_price: Optional[float] = None
    tax_amount: float = 0
    merchant_name: Optional[str] = None
    merchant_location: Optional[str] = None

    @field_validator("expense_date", mode="before")
    def validate_expense_date(cls, value):
        return validate_date_ymd(
            value,
            field="expense_date",
            is_optional=False,
            allowed_future=False,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_description(
            value,
            max_length=500,
            is_optional=False,
            field="description",
        )

    @field_validator("amount", "quantity")
    def validate_positive_amounts(cls, value, info):
        return validate_positive_number(
            value,
            field=info.field_name,
            is_optional=False,
            strictly_positive=True,
        )

    @field_validator("unit_price")
    def validate_unit_price(cls, value):
        return validate_positive_number(
            value,
            field="unit_price",
            is_optional=True,
            strictly_positive=True,
        )

    @field_validator("tax_amount")
    def validate_tax_amount(cls, value):
        return validate_positive_number(
            value,
            field="tax_amount",
            is_optional=True,
            strictly_positive=False,
        )

    @field_validator("merchant_name")
    def validate_merchant_name(cls, value):
        return validate_name_field(
            value,
            max_length=255,
            field="merchant_name",
            is_optional=True,
            only_letters=True,
        )

    @field_validator("merchant_location")
    def validate_merchant_location(cls, value):
        return validate_optional_str(
            value,
            max_length=255,
            field="merchant_location",
        )


class ReimbursementItemCreate(ReimbursementItemBase):
    """Reimbursement item creation schema."""
    receipt_file_id: Optional[UUID] = None
    is_billable: bool = False
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None


class ReimbursementItemResponse(BaseSchema):
    """Reimbursement item response schema."""
    id: UUID
    category_id: UUID
    expense_date: date
    description: str
    amount: float
    quantity: float = 1
    unit_price: Optional[float] = None
    tax_amount: float = 0
    merchant_name: Optional[str] = None
    merchant_location: Optional[str] = None
    receipt_file_id: Optional[UUID] = None
    is_billable: bool
    created_at: datetime


class ReimbursementClaimBase(BaseSchema):
    """Base reimbursement claim schema."""
    staff_id: UUID
    claim_date: date
    total_amount: float
    currency: str = "USD"
    description: Optional[str] = None

    @field_validator("claim_date", mode="before")
    def validate_claim_date(cls, value):
        return validate_date_ymd(
            value,
            field="claim_date",
            is_optional=False,
        )

    @field_validator("total_amount")
    def validate_total_amount(cls, value):
        return validate_positive_number(
            value,
            field="total_amount",
            is_optional=False,
            strictly_positive=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )


class ReimbursementClaimCreate(ReimbursementClaimBase):
    """Reimbursement claim creation schema."""
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    expense_date_start: Optional[date] = None
    expense_date_end: Optional[date] = None
    items: List[ReimbursementItemCreate] = []

    @field_validator("expense_date_start", "expense_date_end", mode="before")
    def validate_expense_dates(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            is_optional=True,
            allowed_future=False,
        )

    @model_validator(mode="after")
    def check_date_order(self):
        if self.expense_date_start and self.expense_date_end:
            if self.expense_date_start > self.expense_date_end:
                raise ValueError("start date must be earlier than end date")
        return self

class ReimbursementClaimUpdate(BaseSchema):
    """Reimbursement claim update schema."""
    status: Optional[ReimbursementStatus] = None
    approval_notes: Optional[str] = None


class ReimbursementClaimResponse(BaseSchema, TimestampSchema):
    """Reimbursement claim response schema."""
    id: UUID
    claim_number: str
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    status: ReimbursementStatus
    submitted_at: Optional[datetime] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    paid_at: Optional[datetime] = None
    payment_reference: Optional[str] = None
    staff_name: Optional[str] = None
    items: List[ReimbursementItemResponse] = []
    staff_id: UUID
    claim_date: date
    total_amount: float
    currency: Optional[str] = None
    description: Optional[str] = None


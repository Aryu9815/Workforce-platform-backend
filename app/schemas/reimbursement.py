"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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


class ReimbursementItemCreate(ReimbursementItemBase):
    """Reimbursement item creation schema."""
    receipt_file_id: Optional[UUID] = None
    is_billable: bool = False
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None


class ReimbursementItemResponse(ReimbursementItemBase):
    """Reimbursement item response schema."""
    id: UUID
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


class ReimbursementClaimCreate(ReimbursementClaimBase):
    """Reimbursement claim creation schema."""
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    expense_date_start: Optional[date] = None
    expense_date_end: Optional[date] = None
    items: List[ReimbursementItemCreate] = []


class ReimbursementClaimUpdate(BaseSchema):
    """Reimbursement claim update schema."""
    status: Optional[ReimbursementStatus] = None
    approval_notes: Optional[str] = None


class ReimbursementClaimResponse(ReimbursementClaimBase, TimestampSchema):
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


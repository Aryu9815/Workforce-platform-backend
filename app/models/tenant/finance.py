import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, DateTime, Date, Time, Boolean, Integer, 
    Numeric, ForeignKey, Index, UniqueConstraint, CheckConstraint,
    ARRAY, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.db_connection import TenantScopedMixin, TenantBase


class ExpenseCategory(TenantBase, TenantScopedMixin):
    """Expense categories for reimbursements."""
    __tablename__ = "expense_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True)
    requires_receipt = Column(Boolean, default=True)
    max_amount = Column(Numeric(12, 2), nullable=True)
    tax_deductible = Column(Boolean, default=False)
    gl_account_code = Column(String(50), nullable=True)

class ReimbursementClaim(TenantBase, TenantScopedMixin):
    """Reimbursement claims."""
    __tablename__ = "reimbursement_claims"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_number = Column(String(50), unique=True, nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    claim_date = Column(Date, nullable=False)
    expense_date_start = Column(Date, nullable=True)
    expense_date_end = Column(Date, nullable=True)
    total_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="INR")
    exchange_rate = Column(Numeric(10, 6), default=1)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="draft")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    gl_exported = Column(Boolean, default=False)
    gl_exported_at = Column(DateTime(timezone=True), nullable=True)
    custom_fields = Column(JSONB, default=dict)


class ReimbursementItem(TenantBase, TenantScopedMixin):
    """Individual items in a reimbursement claim."""
    __tablename__ = "reimbursement_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("reimbursement_claims.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("expense_categories.id", ondelete="RESTRICT"), nullable=False)
    expense_date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Numeric(8, 2), default=1)
    unit_price = Column(Numeric(12, 2), nullable=True)
    tax_amount = Column(Numeric(12, 2), default=0)
    merchant_name = Column(String(255), nullable=True)
    merchant_location = Column(String(255), nullable=True)
    receipt_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    is_billable = Column(Boolean, default=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    custom_fields = Column(JSONB, default=dict)


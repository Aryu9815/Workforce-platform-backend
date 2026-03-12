import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, Date, Boolean, 
    Numeric, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.db_connection import TenantScopedMixin, TenantBase
from app.core.constants import SET_NULL, STAFF_PROFILE_ID, PROJECT_ID, TASK_ID


class ExpenseCategory(TenantBase, TenantScopedMixin):
    """Expense categories for reimbursements."""
    __tablename__ = "expense_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("expense_categories.id", ondelete=SET_NULL), nullable=True)
    requires_receipt = Column(Boolean, default=True)
    max_amount = Column(Numeric(12, 2), nullable=True)
    tax_deductible = Column(Boolean, default=False)
    gl_account_code = Column(String(50), nullable=True)

class ReimbursementClaim(TenantBase, TenantScopedMixin):
    """Reimbursement claims."""
    __tablename__ = "reimbursement_claims"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_number = Column(String(50), unique=True, nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey(PROJECT_ID, ondelete=SET_NULL), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete=SET_NULL), nullable=True)
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
    receipt_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete=SET_NULL), nullable=True)
    is_billable = Column(Boolean, default=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete=SET_NULL), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey(PROJECT_ID, ondelete=SET_NULL), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete=SET_NULL), nullable=True)
    custom_fields = Column(JSONB, default=dict)


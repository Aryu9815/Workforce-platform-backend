"""
SQLAlchemy models for all database entities.
"""
import uuid
from sqlalchemy import (
    Column, String, Text, Date, Boolean, Integer, 
    Numeric, ForeignKey, UniqueConstraint, 
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.db_connection import TenantScopedMixin, TenantBase
from app.core.constants import DEPARTMENT_ID, STAFF_PROFILE_ID, DESIGNATION_ID, SET_NULL

class Department(TenantBase, TenantScopedMixin):
    """Department model."""
    __tablename__ = "departments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey(DEPARTMENT_ID, ondelete=SET_NULL), nullable=True)
    head_id = Column(UUID(as_uuid=True), nullable=True)


class Designation(TenantBase, TenantScopedMixin):
    """Designation/Job title model."""
    __tablename__ = "designations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey(DEPARTMENT_ID, ondelete=SET_NULL), nullable=True)
    description = Column(Text, nullable=True)


class StaffProfile(TenantBase, TenantScopedMixin):
    """Staff profile model."""
    __tablename__ = "staff_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    employee_code = Column(String(50), nullable=True)
    profile_image = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey(DEPARTMENT_ID, ondelete="RESTRICT"), nullable=False)
    designation_id = Column(UUID(as_uuid=True), ForeignKey(DESIGNATION_ID, ondelete="RESTRICT"), nullable=False)
    reporting_manager_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete=SET_NULL), nullable=True)
    employment_type = Column(String(20), nullable=False)  # full_time, contractor, vendor
    join_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=True)
    exit_reason = Column(String(100), nullable=True)
    work_location = Column(String(100), nullable=True)
    skills = Column(JSONB, default=list)
    certifications = Column(JSONB, default=list)
    emergency_contact = Column(JSONB, nullable=True)
    documents = Column(JSONB, default=list)
    custom_fields = Column(JSONB, default=dict)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete=SET_NULL), nullable=True)

class StaffLeaveBalance(TenantBase, TenantScopedMixin):
    __tablename__ = "staff_leave_balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False)

    year = Column(Integer, nullable=False)

    allocated_days = Column(Numeric(5,2), default=0)
    used_days = Column(Numeric(5,2), default=0)
    remaining_days = Column(Numeric(5,2), default=0)

    __table_args__ = (
        UniqueConstraint("staff_id", "leave_type_id", "year"),
    )
    
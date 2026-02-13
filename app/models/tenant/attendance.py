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




class AttendancePolicy(TenantBase, TenantScopedMixin):
    """Attendance policy configuration."""
    __tablename__ = "attendance_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    work_hours_per_day = Column(Numeric(4, 2), default=8.0)
    work_days_per_week = Column(Integer, default=5)
    grace_period_minutes = Column(Integer, default=15)
    overtime_threshold = Column(Numeric(4, 2), default=8.0)
    overtime_calculation = Column(String(20), default="daily")
    is_default = Column(Boolean, default=False)
    rules = Column(JSONB, default=dict)


class Shift(TenantBase, TenantScopedMixin):
    """Work shift definition."""
    __tablename__ = "shifts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    break_duration_minutes = Column(Integer, default=60)
    days_of_week = Column(ARRAY(Integer), nullable=False)
    is_night_shift = Column(Boolean, default=False)


class AttendanceRecord(TenantBase, TenantScopedMixin):
    """Daily attendance records."""
    __tablename__ = "attendance_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    check_in = Column(DateTime(timezone=True), nullable=True)
    check_out = Column(DateTime(timezone=True), nullable=True)
    check_in_location = Column(JSONB, nullable=True)
    check_out_location = Column(JSONB, nullable=True)
    check_in_method = Column(String(20), nullable=True)
    check_out_method = Column(String(20), nullable=True)
    work_hours = Column(Numeric(5, 2), nullable=True)
    overtime_hours = Column(Numeric(5, 2), default=0)
    status = Column(String(20), default="present")  # present, absent, late, half_day
    notes = Column(Text, nullable=True)
    is_manual_entry = Column(Boolean, default=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    

class LeaveType(TenantBase, TenantScopedMixin):
    """Leave type definitions."""
    __tablename__ = "leave_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    is_paid = Column(Boolean, default=True)
    color = Column(String(7), nullable=True)
    requires_approval = Column(Boolean, default=True)
    max_days_per_year = Column(Integer, nullable=True)
    carry_forward = Column(Boolean, default=False)



class LeaveRequest(TenantBase, TenantScopedMixin):
    """Leave requests from staff."""
    __tablename__ = "leave_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="RESTRICT"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_requested = Column(Numeric(4, 1), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    documents = Column(JSONB, default=list)


class Holiday(TenantBase, TenantScopedMixin):
    """Company holidays."""
    __tablename__ = "holidays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(20), default="public")
    is_recurring = Column(Boolean, default=False)
    description = Column(Text, nullable=True)


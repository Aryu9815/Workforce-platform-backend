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
# Attendance Schemas
# ============================================

class AttendanceStatus(str, Enum):
    """Attendance status enum."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    HALF_DAY = "half_day"
    LEAVE = "leave"   # ← ADD THIS

class AttendanceRecordBase(BaseSchema):
    """Base attendance record schema."""
    staff_id: UUID
    date: date
    shift_id: Optional[UUID] = None
    status: AttendanceStatus = AttendanceStatus.PRESENT
    notes: Optional[str] = None


class AttendanceRecordCreate(AttendanceRecordBase):
    """Attendance record creation schema."""
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    check_in_location: Optional[Dict[str, Any]] = None
    check_out_location: Optional[Dict[str, Any]] = None
    check_in_method: Optional[str] = None
    check_out_method: Optional[str] = None
    is_manual_entry: bool = False


class AttendanceRecordUpdate(BaseSchema):
    """Attendance record update schema."""
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: Optional[AttendanceStatus] = None
    notes: Optional[str] = None


class AttendanceRecordResponse(AttendanceRecordBase, TimestampSchema):
    """Attendance record response schema."""
    id: UUID
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_hours: Optional[float] = None
    overtime_hours: Optional[float] = 0.0
    is_manual_entry: Optional[bool] = False
    approved_by: Optional[UUID] = None
    staff_name: Optional[str] = None
    staff_name: Optional[str] = None

# ============================================
# Leave Schemas
# ============================================

class LeaveStatus(str, Enum):
    """Leave status enum."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveRequestBase(BaseSchema):
    """Base leave request schema."""
    staff_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    days_requested: float
    reason: Optional[str] = None


class LeaveRequestCreate(LeaveRequestBase):
    """Leave request creation schema."""
    documents: List[Dict[str, Any]] = []


class LeaveRequestUpdate(BaseSchema):
    """Leave request update schema."""
    status: Optional[LeaveStatus] = None
    approval_notes: Optional[str] = None


class LeaveRequestResponse(LeaveRequestBase, TimestampSchema):
    """Leave request response schema."""
    id: UUID
    status: LeaveStatus
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    documents: List[Dict[str, Any]]
    staff_name: Optional[str] = None
    leave_type_name: Optional[str] = None


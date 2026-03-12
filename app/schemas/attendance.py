"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import field_validator, model_validator
from enum import Enum
from app.schemas.base_schema import BaseSchema, TimestampSchema
from app.schemas.task_work_schemas import TaskWorkResponse
from app.schemas.validators import (
    validate_code_field,
    validate_date_ymd,
    validate_description,
    validate_name_field,
    validate_optional_str,
    validate_positive_number,
)

# ============================================
# Attendance Schemas
# ============================================

class AttendanceStatus(str, Enum):
    """Attendance status enum."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    HALF_DAY = "half_day"
    LEAVE = "leave"

class AttendanceRecordBase(BaseSchema):
    """Base attendance record schema."""
    staff_id: UUID
    date: date
    shift_id: Optional[UUID] = None
    status: AttendanceStatus = AttendanceStatus.PRESENT
    notes: Optional[str] = None

    @field_validator("date")
    def validate_date(cls, value):
        return validate_date_ymd(value)
    
    @field_validator("notes")
    def validate_notes(cls, value):
        return validate_optional_str(value, max_length=500, field="notes")

class AttendanceRecordCreate(AttendanceRecordBase):
    """Attendance record creation schema."""
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    check_in_location: Optional[Dict[str, Any]] = None
    check_out_location: Optional[Dict[str, Any]] = None
    check_in_method: Optional[str] = None
    check_out_method: Optional[str] = None
    is_manual_entry: bool = False

    @field_validator("check_in", "check_out")
    def validate_datetime(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            is_datetime=True,
        )

class AttendanceRecordUpdate(BaseSchema):
    """Attendance record update schema."""
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: Optional[AttendanceStatus] = None
    notes: Optional[str] = None

    @field_validator("check_in", "check_out")
    def validate_datetime(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            is_datetime=True,
            is_optional=True,
        )

    @field_validator("notes")
    def validate_notes(cls, value):
        return validate_optional_str(value, max_length=500, field="notes")

class AttendanceRecordResponse(BaseSchema, TimestampSchema):
    """Attendance record response schema."""
    id: UUID
    staff_id: UUID
    date: date
    shift_id: Optional[UUID] = None
    status: AttendanceStatus
    notes: Optional[str] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_hours: Optional[float] = None
    overtime_hours: Optional[float] = 0.0
    is_manual_entry: Optional[bool] = False
    approved_by: Optional[UUID] = None
    staff_name: Optional[str] = None
    # task_time_log : List[Dict[str, Any]] = []
class AttendanceRecordDetailResponse(AttendanceRecordResponse):
    """Detailed attendance record response with task work sessions."""
    task_work_sessions: List[TaskWorkResponse] = []
from pydantic import BaseModel
class AttendanceNotesUpdate(BaseModel):
    notes: Optional[str] = None
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

    @field_validator("start_date", "end_date")
    def validate_dates(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            allowed_past=False
        )

    @field_validator("reason")
    def validate_reason(cls, value):
        return validate_optional_str(value, max_length=500, field="reason")
    
    @field_validator("days_requested")
    def validate_days_requested(cls, value):
        return validate_positive_number(
            value,
            field="days_requested",
            strictly_positive=True,
        )
    
    @model_validator(mode="after")
    def check_date_order(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start date must be earlier than end date")
        return self

class LeaveRequestCreate(LeaveRequestBase):
    """Leave request creation schema."""
    documents: List[Dict[str, Any]] = []


class LeaveRequestUpdate(BaseSchema):
    """Leave request update schema."""
    status: Optional[LeaveStatus] = None
    approval_notes: Optional[str] = None

    @field_validator("approval_notes")
    def validate_approval_notes(cls, value):
        return validate_optional_str(value, max_length=500, field="approval_notes")
    
class LeaveRequestResponse(BaseSchema, TimestampSchema):
    """Leave request response schema."""
    id: UUID
    staff_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    days_requested: float
    reason: Optional[str] = None
    status: LeaveStatus
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None
    documents: List[Dict[str, Any]]
    staff_name: Optional[str] = None
    leave_type_name: Optional[str] = None

from pydantic import BaseModel, field_validator
from typing import Optional

class LeaveTypeRequestCreate(BaseModel):
    name: str
    code: str
    description: str
    is_paid: Optional[bool] = False
    color: Optional[str] = None
    requires_approval: Optional[bool] = True
    max_days_per_year: Optional[int] = None
    carry_forward: Optional[bool] = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        return validate_name_field(value, max_length=100, field="name")

    @field_validator("code")
    @classmethod
    def validate_code(cls, value):
        return validate_code_field(value, field="code", max_length=20)

    @field_validator("description")
    @classmethod
    def validate_description_field(cls, value):
        return validate_description(value, max_length=500, field="description")

    @field_validator("color")
    @classmethod
    def validate_color(cls, value):
        if value is not None and not isinstance(value, str):
            raise ValueError("Color must be a string in hex format (e.g., #RRGGBB)")
        return value

    @field_validator("max_days_per_year")
    @classmethod
    def validate_max_days(cls, value):
        if value is not None and value < 0:
            raise ValueError("max_days_per_year must be non-negative")
        return value
    
class LeaveTypeResponse(BaseSchema, TimestampSchema):
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    is_paid: bool
    color: Optional[str] = None
    requires_approval: bool
    max_days_per_year: Optional[int] = None
    carry_forward: bool
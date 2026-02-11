
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
    

class StaffBase(BaseSchema):
    """Base staff schema."""
    employee_code: Optional[str] = None
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    department_id: UUID
    designation_id: UUID
    reporting_manager_id: Optional[UUID] = None
    employment_type: str = "full_time"
    join_date: date
    work_location: Optional[str] = None


class StaffCreate(StaffBase):
    """Staff creation schema."""
    skills: List[str] = []
    certifications: List[Dict[str, Any]] = []
    emergency_contact: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class StaffUpdate(BaseSchema):
    """Staff update schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None
    reporting_manager_id: Optional[UUID] = None
    employment_type: Optional[str] = None
    work_location: Optional[str] = None
    skills: Optional[List[str]] = None
    is_active: Optional[bool] = None


class StaffResponse(StaffBase, TimestampSchema):
    """Staff response schema."""
    id: UUID
    user_id: Optional[UUID] = None
    exit_date: Optional[date] = None
    exit_reason: Optional[str] = None
    skills: List[str]
    is_active: bool
    full_name: str
    department_name: Optional[str] = None
    designation_name: Optional[str] = None





"""
Pydantic schemas for API request/response validation.
"""
from datetime import date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import EmailStr, Field, field_validator
from app.schemas.base_schema import BaseSchema, TimestampSchema
from app.schemas.validators import (
    validate_date_ymd,
    validate_name_field,
    validate_optional_str,
    validate_phone_number,
)

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
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    @field_validator("first_name", "last_name")
    def validate_names(cls, value, info):
        return validate_name_field(
            value,
            max_length=100,
            field=info.field_name,
            only_letters=True
        )

    @field_validator("phone")
    def validate_phone(cls, value):
        return validate_phone_number(value, is_optional=True)

    @field_validator("work_location")
    def validate_work_location(cls, value):
        return validate_optional_str(
            value,
            max_length=150,
            field="work_location",
        )

    @field_validator("join_date", mode="before")
    def validate_join_date(cls, value):
        return validate_date_ymd(
            value,
            field="join_date",
            is_optional=False,
        )


class StaffCreate(StaffBase):
    """Staff creation schema."""
    skills: List[str] = []
    certifications: List[Dict[str, Any]] = []
    emergency_contact: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    role_id:Optional[UUID]=None
    @field_validator("reporting_manager_id", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v


class StaffUpdate(BaseSchema):
    """Staff update schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None
    reporting_manager_id: Optional[UUID] = None
    employment_type: Optional[str] = None
    work_location: Optional[str] = None
    skills: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("first_name", "last_name")
    def validate_names(cls, value, info):
        return validate_name_field(
            value,
            max_length=100,
            field=info.field_name,
            is_optional=True,
            only_letters=True
        )

    @field_validator("phone")
    def validate_phone(cls, value):
        return validate_phone_number(value, is_optional=True)

    @field_validator("work_location")
    def validate_work_location(cls, value):
        return validate_optional_str(
            value,
            max_length=150,
            field="work_location",
        )


class StaffResponse(BaseSchema, TimestampSchema):
    """Staff response schema."""
    id: UUID
    user_id: Optional[UUID] = None
    exit_date: Optional[date] = None
    exit_reason: Optional[str] = None
    skills: List[str]
    is_active: bool
    full_name: Optional[str] = None
    department_name: Optional[str] = None
    designation_name: Optional[str] = None
    employee_code: Optional[str] = None
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    department_id: UUID
    designation_id: UUID
    role_id: Optional[UUID] = None
    reporting_manager_id: Optional[UUID] = None
    employment_type: str = "full_time"
    join_date: date
    work_location: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class StaffNameResponse(BaseSchema):
    """Schema for staff name and ID."""
    id: UUID | str
    full_name: str

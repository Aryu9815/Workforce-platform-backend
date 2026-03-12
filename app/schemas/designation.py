
"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator

from app.schemas.validators import (
    validate_name_field,
    validate_optional_str,
    validate_positive_number
)


class DesignationCreate(BaseModel):
    name: str
    level: Optional[int] = None
    department_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: bool = True

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value, max_length=100, field="name", only_letters=True)

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )
    @field_validator('level')
    def validate_level(cls, value):
        return validate_positive_number(value, field='level', is_optional=True)


class DesignationUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    department_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=100,
            field="name",
            only_letters=True,
            is_optional=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )

    @field_validator('level')
    def validate_level(cls, value):
        return validate_positive_number(value, field='level', is_optional=True)

class DesignationResponse(BaseModel):
    id: UUID
    name: str
    level: Optional[int] = None
    department_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

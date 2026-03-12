

"""
Pydantic schemas for API request/response validation.
"""
from typing import Optional
from uuid import UUID
from pydantic import Field, field_validator
from app.schemas.validators import (
    validate_code_field,
    validate_name_field,
    validate_optional_str,
)
from app.schemas.base_schema import BaseSchema, TimestampSchema

class DepartmentBase(BaseSchema):
    """Base department schema."""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(None, max_length=20)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    head_id: UUID


    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value, max_length=100, field="name", only_letters=True)

    @field_validator("code")
    def validate_code(cls, value):
        return validate_code_field(
            value,
            field="code",
            max_length=20,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )


class DepartmentCreate(DepartmentBase):
    """Department creation schema."""
    pass


class DepartmentUpdate(BaseSchema):
    """Department update schema."""
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[UUID] = None
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

    @field_validator("code")
    def validate_code(cls, value):
        return validate_code_field(
            value,
            field="code",
            max_length=20,
            is_optional=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )


class DepartmentResponse(BaseSchema, TimestampSchema):
    """Department response schema."""
    id: UUID
    name: str 
    code: Optional[str]
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    head_id: Optional[UUID] = None
    is_active: bool
    staff_count: int = 0

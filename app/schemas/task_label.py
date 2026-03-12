from typing import Optional
from uuid import UUID
from pydantic import Field, field_validator
from app.schemas.base_schema import BaseSchema, TimestampSchema
from app.schemas.validators import validate_name_field, validate_optional_str


class TaskLabelBase(BaseSchema):
    label: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = "#CCCCCC"

    @field_validator('label')
    def validate_label(cls, value):
        return validate_name_field(value, max_length=50, field="label", only_letters=True)

    @field_validator('description')
    def validate_description(cls, value):
        return validate_optional_str(
            value,
            max_length=200,
            field="description"
        )


class TaskLabelCreate(TaskLabelBase):
    project_id: UUID


class TaskLabelUpdate(BaseSchema):
    label: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = None

    @field_validator('label')
    def validate_label(cls, value):
        return validate_name_field(
            value, 
            max_length=50, 
            field="label",
            is_optional=True,
             only_letters=True
        )

    @field_validator('description')
    def validate_description(cls, value):
        return validate_optional_str(
            value,
            max_length=200,
            field="description"
        )

class TaskLabelResponse(BaseSchema, TimestampSchema):
    id: UUID
    label: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    color: Optional[str] = "#CCCCCC"
    project_id: UUID
    created_by: str
    updated_by: Optional[str] = None
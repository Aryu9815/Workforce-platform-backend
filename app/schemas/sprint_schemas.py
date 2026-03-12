
from datetime import date
from typing import Optional
from uuid import UUID
from enum import Enum
from pydantic import Field, field_validator
from app.schemas.base_schema import BaseSchema, TimestampSchema
from app.schemas.validators import (
    validate_date_ymd,
    validate_name_field,
    validate_optional_str,
    validate_positive_number,
)


class IssuseStatus(str, Enum):
    """Task priority enum."""
    BACKLOG = "backlog"
    NEXT_SPRINT = "next_sprint"
    NEW_SPRINT = "new_sprint"

class SprintStatus(str, Enum):
    """Task priority enum."""
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SprintBase(BaseSchema):
    """Base task schema."""
    name: str = Field(..., min_length=1, max_length=500)
    goal: Optional[str] = None
    status: SprintStatus = SprintStatus.PLANNED
    capacity: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value, max_length=500, field="name")

    @field_validator("goal")
    def validate_goal(cls, value):
        return validate_optional_str(
            value,
            max_length=1000,
            field="goal",
        )

    @field_validator("capacity")
    def validate_capacity(cls, value):
        return validate_positive_number(
            value,
            field="capacity",
            is_optional=True,
            strictly_positive=True,
        )

    @field_validator("start_date", "end_date", mode="before")
    def validate_dates(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            is_optional=True,
        )


class SprintCreate(SprintBase):
    """Task creation schema."""
    project_id: UUID


class SprintUpdate(BaseSchema):
    """Task update schema."""
    name: Optional[str] = None
    goal: Optional[str] = None
    status: Optional[SprintStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    capacity: Optional[int] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=500,
            field="name",
            is_optional=True,
        )

    @field_validator("goal")
    def validate_goal(cls, value):
        return validate_optional_str(
            value,
            max_length=1000,
            field="goal",
        )

    @field_validator("capacity")
    def validate_capacity(cls, value):
        return validate_positive_number(
            value,
            field="capacity",
            is_optional=True,
            strictly_positive=True,
        )

    @field_validator("start_date", "end_date", mode="before")
    def validate_dates(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            is_optional=True,
        )

class SprintResponse(BaseSchema, TimestampSchema):
    """Task response schema."""
    id: UUID
    project_id: UUID
    name: str
    goal: Optional[str] = None
    sprint_number: Optional[int] = None
    status: SprintStatus = SprintStatus.PLANNED
    capacity: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_by: UUID
    updated_by: Optional[UUID] = None

class SprintEnd(BaseSchema):
    """Sprint end schema."""
    sprint_id: UUID
    move_open_issues_to: IssuseStatus = IssuseStatus.BACKLOG
    new_sprint: Optional[SprintCreate] = None
    next_sprint: Optional[UUID] = None
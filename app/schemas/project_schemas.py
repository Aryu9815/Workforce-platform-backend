
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum
from pydantic import Field, field_validator, model_validator
from app.schemas.base_schema import BaseSchema, TimestampSchema
from app.schemas.validators import (
    validate_date_ymd,
    validate_name_field,
    validate_optional_str,
    validate_positive_number,
    validate_code_field
)


class ProjectStatus(str, Enum):
    """Project status enum."""
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"


class ProjectPriority(str, Enum):
    """Project priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectBase(BaseSchema):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(None, max_length=50)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANNING
    priority: ProjectPriority = ProjectPriority.MEDIUM
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    currency: str = "USD"

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value, max_length=255, field="name")

    @field_validator("code")
    def validate_code(cls, value):
        return validate_code_field(
            value,
            field="code",
            max_length=50
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=1000,
            field="description",
        )

    @field_validator("start_date", "end_date", mode="before")
    def validate_dates(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            is_optional=True,
        )

    @field_validator("budget")
    def validate_budget(cls, value):
        return validate_positive_number(
            value,
            field="budget",
            is_optional=True,
            strictly_positive=True,
        )

    @model_validator(mode="after")
    def check_date_order(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be earlier than end_date")
        return self
    
class ProjectCreate(ProjectBase):
    """Project creation schema."""
    project_manager_id: UUID
    parent_project_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    location: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    workflow_id: Optional[UUID] = None


class ProjectUpdate(BaseSchema):
    """Project update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[ProjectPriority] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    budget: Optional[float] = None
    cost_estimate: Optional[float] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    project_manager_id: Optional[UUID] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=255,
            field="name",
            is_optional=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=1000,
            field="description",
        )

    @field_validator(
        "start_date",
        "end_date",
        "actual_start_date",
        "actual_end_date",
        mode="before",
    )
    def validate_dates(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            is_optional=True,
        )

    @field_validator("budget", "cost_estimate")
    def validate_money_fields(cls, value, info):
        return validate_positive_number(
            value,
            field=info.field_name,
            is_optional=True,
            strictly_positive=True,
        )

    @model_validator(mode="after")
    def check_date_order(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start date must be earlier than end date")
        if self.actual_start_date and self.actual_end_date and self.actual_start_date > self.actual_end_date:
            raise ValueError("actual start date must be earlier than actual end date")
        return self
    

class ProjectMemberBase(BaseSchema):
    project_id: UUID
    staff_id: UUID
    role: str = Field(..., min_length=1, max_length=100)
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None

    @field_validator("role")
    def validate_role(cls, value):
        # Treat role similar to a name field (alphanumeric + spaces)
        return validate_name_field(value, max_length=100, field="role")


class CreateProjectMember(ProjectMemberBase):
    pass

class UpdateProjectMember(BaseSchema):
    role: Optional[str] = None
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    is_deleted: Optional[bool] = None
    is_active: Optional[bool] = None
    is_removed: Optional[bool] = None
    updated_by: Optional[str] = None



class ProjectMemberResponse(TimestampSchema):
    """Project response schema."""
    id: UUID
    project_id: Optional[UUID] = None
    staff_id: Optional[UUID] = None
    role: Optional[str] = None
    joined_at: Optional[datetime] = None    
    left_at: Optional[datetime] = None
    is_removed: Optional[bool] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None
    name: Optional[str] = None
    designation: Optional[str] = None

class ProjectResponse(BaseSchema, TimestampSchema):
    """Project response schema."""
    id: UUID
    parent_project_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    project_manager_id: UUID
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    cost_estimate: Optional[float] = None
    actual_cost: float
    progress_percentage: int
    is_template: bool
    deleted_at: Optional[datetime] = None
    manager_name: Optional[str] = None
    project_members: List[ProjectMemberResponse] = []
    workflow_id: Optional[UUID] = None
    name: str
    code: Optional[str] 
    description: Optional[str] = None
    status: ProjectStatus
    priority: ProjectPriority
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    currency: Optional[str] = None
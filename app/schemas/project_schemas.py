
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


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



class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)

class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ProjectBase(BaseSchema):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANNING
    priority: ProjectPriority = ProjectPriority.MEDIUM
    project_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    currency: str = "USD"


class ProjectCreate(ProjectBase):
    """Project creation schema."""
    project_manager_id: UUID
    parent_project_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    location: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None


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


class ProjectMemberBase(BaseSchema):
    project_id: UUID
    staff_id: UUID
    role: str = Field(..., min_length=1, max_length=100)
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None


class CreateProjectMember(ProjectMemberBase):
    pass

class UpdateProjectMember(BaseSchema):
    role: Optional[str] = None
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    is_deleted: Optional[bool] = None
    is_active: Optional[bool] = None
    is_removed: Optional[bool] = None



class ProjectMemberResponse(TimestampSchema):
    """Project response schema."""
    id: UUID
    project_id: Optional[UUID] = None
    staff_id: Optional[UUID] = None
    role: Optional[str] = None
    joined_at: Optional[date] = None    
    left_at: Optional[date] = None
    is_removed: Optional[bool] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None
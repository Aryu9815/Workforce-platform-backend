
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)
    
class TaskPriority(str, Enum):
    """Task priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(BaseSchema):
    """Base task schema."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    task_type: Optional[str] = None
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    """Task creation schema."""
    project_id: UUID
    parent_task_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    assignee_ids: List[UUID] = []
    milestone: bool = False
    billable: bool = True
    location: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    tags: List[str] = []


class TaskUpdate(BaseSchema):
    """Task update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    status_id: Optional[UUID] = None
    priority: Optional[TaskPriority] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    billable: Optional[bool] = None
    tags: Optional[List[str]] = None


class TaskResponse(TaskBase, TimestampSchema):
    """Task response schema."""
    id: UUID
    project_id: UUID
    parent_task_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    status_name: Optional[str] = None
    status_color: Optional[str] = None
    actual_hours: float
    actual_cost: float
    completed_at: Optional[datetime] = None
    created_by: UUID
    progress_percentage: int
    milestone: bool
    billable: bool
    deleted_at: Optional[datetime] = None
    assignees: List[Dict[str, Any]] = []

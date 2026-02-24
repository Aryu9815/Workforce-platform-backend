
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
    ticket_number: Optional[int] = None
    ticket_code: Optional[str] = None


class TaskCreate(TaskBase):
    """Task creation schema."""
    project_id: UUID
    sprint_id: UUID
    parent_task_id: Optional[UUID] = None
    milestone: bool = False
    billable: bool = True
    location: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    assignee_ids: List[UUID] = []


class TaskUpdate(BaseSchema):
    """Task update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    workflow_state_id: Optional[UUID] = None
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
    sprint_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    workflow_state_id: Optional[UUID] = None
    workflow_state_name: Optional[str] = None
    actual_hours: float
    actual_cost: float
    updated_by: Optional[UUID] = None
    created_by: UUID
    progress_percentage: int
    milestone: bool
    billable: bool
    assignees: List[Dict[str, Any]] = []
    ticket: Optional[str] = None

class CommentBase(BaseSchema):
    """Base comment schema."""
    content: str
    is_internal: bool = False
    parent_comment_id: Optional[UUID] = None


class CommentCreate(CommentBase):
    """Comment creation schema."""
    task_id: UUID


class CommentUpdate(BaseSchema):
    """Comment update schema."""
    content: Optional[str] = None
    is_internal: Optional[bool] = None

class CommentResponse(CommentBase, TimestampSchema):
    """Comment response schema."""
    id: UUID
    task_id: UUID
    user_id: UUID
    updated_by: Optional[UUID] = None
    created_by: UUID
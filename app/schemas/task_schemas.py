
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum
from pydantic import Field, field_validator, model_validator
from app.schemas.base_schema import BaseSchema, TimestampSchema
from app.schemas.validators import (
    validate_date_ymd,
    validate_description,
    validate_name_field,
    validate_optional_str,
    validate_positive_number,
)

class TaskPriority(str, Enum):
    """Task priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskAssigneeRole(str, Enum):
    """ Task assignee's role"""
    ASSIGNEE = 'assignee'
    COLLABORATOR = 'collaborator'
    REPORTER = 'reporter'
    TESTER = 'tester'

class TaskAssigneeBase(BaseSchema):
    staff_id: UUID
    role: Optional[TaskAssigneeRole] = 'assignee'


class TaskBase(BaseSchema):
    """Base task schema."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    ticket_number: Optional[int] = None
    ticket_code: Optional[str] = None

    @field_validator("title")
    def validate_title(cls, value):
        return validate_name_field(value, max_length=500, field="title")

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=2000,
            field="description",
        )

    @field_validator("estimated_hours", "estimated_cost")
    def validate_estimates(cls, value, info):
        return validate_positive_number(
            value,
            field=info.field_name,
            is_optional=True,
            strictly_positive=True,
        )

    @field_validator("start_date", "due_date", mode="before")
    def validate_dates(cls, value, info):
        return validate_date_ymd(
            value,
            field=info.field_name,
            is_optional=True,
        )

    @model_validator(mode="after")
    def check_date_order(self):
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValueError("start date must be earlier than due date")
        return self
    

class TaskCreate(TaskBase):
    """Task creation schema."""
    project_id: UUID
    sprint_id: UUID
    parent_task_id: Optional[UUID] = None
    milestone: bool = False
    billable: bool = True
    location: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    assignees: Optional[List[TaskAssigneeBase]] = []
    is_blocked_by_task: Optional[bool] = False

    @model_validator(mode="after")
    def validate_assignees(self):
        try:
            DEFAULT_ROLE_DICT = ['assignee','reporter','tester']
            [DEFAULT_ROLE_DICT.remove(assignee.role) for assignee in self.assignees if assignee.role != 'collaborator']
        except Exception as e:
            print(123213, str(e))
            raise ValueError(f"Invalid role: You can assign role (Assignee, Reporter, Tester) to one member only")
        return self

    @model_validator(mode="after")
    def validate_block_task(self):
        if self.is_blocked_by_task and self.parent_task_id is None:
            raise ValueError(f"Cannot block task without parent task")
        return self



class TaskUpdate(BaseSchema):
    """Task update schema."""
    title: Optional[str] = None
    task_label_id: Optional[UUID] = None
    description: Optional[str] = None
    workflow_state_id: Optional[UUID] = None
    priority: Optional[TaskPriority] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    due_date: Optional[date] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    billable: Optional[bool] = None
    tags: Optional[List[str]] = None

    @field_validator("title")
    def validate_title(cls, value):
        return validate_name_field(
            value,
            max_length=500,
            field="title",
            is_optional=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=2000,
            field="description",
        )

    @field_validator("estimated_hours", "actual_hours")
    def validate_hours(cls, value, info):
        return validate_positive_number(
            value,
            field=info.field_name,
            is_optional=True,
            strictly_positive=True,
        )

    @field_validator("due_date", mode="before")
    def validate_due_date(cls, value):
        return validate_date_ymd(
            value,
            field="due_date",
            is_optional=True,
        )

class TaskLabelInfo(BaseSchema):
    id: UUID
    label: str
    description: Optional[str] = None
    color: Optional[str] = None

class TaskAuditResponse(BaseSchema, TimestampSchema):
    id: UUID
    task_id: UUID
    action: str
    field_name: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    performed_by: UUID
class TaskResponse(BaseSchema, TimestampSchema):
    """Task response schema."""
    id: UUID
    project_id: UUID
    sprint_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    workflow_state_id: Optional[UUID] = None
    workflow_state_name: Optional[str] = None
    actual_hours: float
    actual_cost: float
    task_label_id: Optional[UUID] = None
    task_label: Optional[TaskLabelInfo] = None
    updated_by: Optional[UUID] = None
    created_by: UUID
    progress_percentage: int
    milestone: bool
    billable: bool
    assignees: List[Dict[str, Any]] = []
    ticket: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    completed_at: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    ticket_number: Optional[int] = None
    ticket_code: Optional[str] = None
    audit_logs: List[TaskAuditResponse] = []
    activities: List[str] = []

class CommentBase(BaseSchema):
    """Base comment schema."""
    content: str
    is_internal: bool = False
    parent_comment_id: Optional[UUID] = None

    @field_validator("content")
    def validate_content(cls, value):
        return validate_description(
            value,
            max_length=2000,
            is_optional=False,
            field="content",
        )


class CommentCreate(CommentBase):
    """Comment creation schema."""
    task_id: UUID


class CommentUpdate(BaseSchema):
    """Comment update schema."""
    content: Optional[str] = None
    is_internal: Optional[bool] = None

    @field_validator("content")
    def validate_content(cls, value):
        return validate_optional_str(
            value,
            max_length=2000,
            field="content",
        )

class CommentResponse(BaseSchema, TimestampSchema):
    """Comment response schema."""
    id: UUID
    task_id: UUID
    user_id: UUID
    content: str
    is_internal: bool = False
    parent_comment_id: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_by: UUID

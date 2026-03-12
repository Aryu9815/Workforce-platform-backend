import uuid
from sqlalchemy import (
    TIMESTAMP, Column, String, Text, DateTime, Date, Boolean, Integer, 
    Numeric, ForeignKey, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.db_connection import TenantScopedMixin, TenantBase
from app.core.constants import TASK_ID, SET_NULL, PROJECT_ID, STAFF_PROFILE_ID

class TaskLabel(TenantBase, TenantScopedMixin):
    """Task labels."""
    __tablename__ = "task_labels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(PROJECT_ID, ondelete="CASCADE"), nullable=False)
    label = Column(String(50), nullable=False)
    description = Column(String(200), nullable=True)
    color = Column(String(20), default="#CCCCCC")
    

class Task(TenantBase, TenantScopedMixin):
    """Task model."""
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(PROJECT_ID, ondelete="CASCADE"), nullable=False)
    task_label_id = Column(UUID(as_uuid=True), ForeignKey("task_labels.id", ondelete=SET_NULL), nullable=True)
    sprint_id = Column(UUID(as_uuid=True), ForeignKey("sprints.id", ondelete=SET_NULL), nullable=True)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete="CASCADE"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    workflow_state_id = Column(UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="RESTRICT"), nullable=True)
    priority = Column(String(20), default="medium")
    estimated_hours = Column(Numeric(6, 2), nullable=True)
    actual_hours = Column(Numeric(6, 2), default=0)
    estimated_cost = Column(Numeric(12, 2), nullable=True)
    actual_cost = Column(Numeric(12, 2), default=0)
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    assigned_by = Column(UUID(as_uuid=True), nullable=True)
    progress_percentage = Column(Integer, default=0)
    milestone = Column(Boolean, default=False)
    billable = Column(Boolean, default=True)
    location = Column(JSONB, nullable=True)
    custom_fields = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    ticket_code = Column(String(50),  nullable=True)
    ticket_number = Column(Integer, nullable=True)
    is_blocked_by_task = Column(Boolean, default=False)

class TaskAssignee(TenantBase, TenantScopedMixin):
    """Task assignees."""
    __tablename__ = "task_assignees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(UUID(as_uuid=True), nullable=False)
    is_primary = Column(Boolean, default=False)
    role = Column(String, default='assignee')
    allocation_percentage = Column(Integer, default=100)
    


class TaskDependency(TenantBase, TenantScopedMixin):
    """Task dependencies."""
    __tablename__ = "task_dependencies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String(20), default="finish_to_start")
    lag_days = Column(Integer, default=0)
    

class TaskComment(TenantBase, TenantScopedMixin):
    """Task comments."""
    __tablename__ = "task_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("task_comments.id", ondelete="CASCADE"), nullable=True)

class TaskAttachments(TenantBase, TenantScopedMixin):
    """Task comments."""
    __tablename__ = "task_attachments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
    description = Column(Text, nullable=False)

class TaskAudit(TenantBase):
    __tablename__ = "task_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey(TASK_ID, ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    action = Column(String(50), nullable=False)  
    # CREATE / UPDATE / DELETE / STATUS_CHANGE / ASSIGNEE_CHANGE

    field_name = Column(String(100), nullable=True)

    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)

    performed_by = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
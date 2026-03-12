import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, Date,  Boolean, Integer, 
    Numeric, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.db_connection import TenantScopedMixin, TenantBase
from app.core.constants import SET_NULL, PROJECT_ID, STAFF_PROFILE_ID

class Project(TenantBase, TenantScopedMixin):
    """Project model."""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="planning")
    priority = Column(String(20), default="medium")
    parent_project_id = Column(UUID(as_uuid=True), ForeignKey(PROJECT_ID, ondelete=SET_NULL), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete=SET_NULL), nullable=True)
    project_manager_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete="RESTRICT"), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    budget = Column(Numeric(15, 2), nullable=True)
    cost_estimate = Column(Numeric(15, 2), nullable=True)
    actual_cost = Column(Numeric(15, 2), default=0)
    currency = Column(String(3), default="USD")
    progress_percentage = Column(Integer, default=0)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete=SET_NULL), nullable=True)
    location = Column(JSONB, nullable=True)
    settings = Column(JSONB, default=dict)
    custom_fields = Column(JSONB, default=dict)
    is_template = Column(Boolean, default=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey(PROJECT_ID, ondelete=SET_NULL), nullable=True)


class ProjectMember(TenantBase, TenantScopedMixin):
    """Project membership."""
    __tablename__ = "project_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(PROJECT_ID, ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete="CASCADE"), nullable=False)
    role = Column(String(100), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    permissions = Column(JSONB, default=list)
    is_removed = Column(Boolean, default=False)


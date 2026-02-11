import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, DateTime, Date, Time, Boolean, Integer, 
    Numeric, ForeignKey, Index, UniqueConstraint, CheckConstraint,
    ARRAY, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func

from app.db.base import Base
from app.db.db_connection import TenantScopedMixin, TenantBase


class Project(TenantBase, TenantScopedMixin):
    """Project model."""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="planning")
    priority = Column(String(20), default="medium")
    project_type = Column(String(50), nullable=True)
    parent_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    project_manager_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="RESTRICT"), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    budget = Column(Numeric(15, 2), nullable=True)
    cost_estimate = Column(Numeric(15, 2), nullable=True)
    actual_cost = Column(Numeric(15, 2), default=0)
    currency = Column(String(3), default="USD")
    progress_percentage = Column(Integer, default=0)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    location = Column(JSONB, nullable=True)
    settings = Column(JSONB, default=dict)
    custom_fields = Column(JSONB, default=dict)
    is_template = Column(Boolean, default=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)


class ProjectMember(TenantBase, TenantScopedMixin):
    """Project membership."""
    __tablename__ = "project_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(100), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    permissions = Column(JSONB, default=list)
    is_removed = Column(Boolean, default=False)


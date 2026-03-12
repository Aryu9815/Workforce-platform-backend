"""
SQLAlchemy models for all database entities.
"""
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


class Workflow(TenantBase, TenantScopedMixin):
    """Workflow definitions."""
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    entity_type = Column(String(50), nullable=False)
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    settings = Column(JSONB, default=dict)


class WorkflowState(TenantBase, TenantScopedMixin):
    """Workflow state definitions."""
    __tablename__ = "workflow_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False)
    is_initial = Column(Boolean, default=False)
    is_final = Column(Boolean, default=False)
    color = Column(String(7), nullable=True)
    category = Column(String(20), nullable=True)
    requires_assignment = Column(Boolean, default=False)
    time_limit_hours = Column(Integer, nullable=True)


class WorkflowTransitions(TenantBase, TenantScopedMixin):
    """Workflow state definitions."""
    __tablename__ = "workflow_transitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    from_state_id = Column(UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False)
    to_state_id = Column(UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    request_approval = Column(Boolean, default=False)
    auto_transition = Column(Boolean, default=False)
    condition_rules = Column(JSONB, nullable=True)

class TransitionsRules(TenantBase, TenantScopedMixin):
    """Workflow state definitions."""
    __tablename__ = "transition_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transition_id = Column(UUID(as_uuid=True), ForeignKey("workflow_transitions.id", ondelete="CASCADE"), nullable=False)
    rule_type = Column(String(50), nullable=False)
    rule_config = Column(JSONB, nullable=False)
    error_message = Column(String(255), nullable=True)

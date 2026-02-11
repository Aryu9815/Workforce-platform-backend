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


class ApprovalFlow(TenantBase, TenantScopedMixin):
    __tablename__ = "approval_flows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    entity_type = Column(String(50), nullable=False)
    is_default = Column(Boolean, default=False)
    conditions = Column(JSONB)  # auto-assignment rules

class ApprovalStep(TenantBase, TenantScopedMixin):
    __tablename__ = "approval_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("approval_flows.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, nullable=False)
    approver_type = Column(String(30), nullable=False)  # user / role / manager / department_head
    approver_id = Column(UUID(as_uuid=True)) 
    approver_role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"))
    is_parallel = Column(Boolean, default=False)
    minimum_approvals = Column(Integer, default=1)
    sla_hours = Column(Integer)
    escalation_step_id = Column(UUID(as_uuid=True), ForeignKey("approval_steps.id", ondelete="SET NULL"))
    conditions = Column(JSONB)  
    

class ApprovalInstance(TenantBase, TenantScopedMixin):
    __tablename__ = "approval_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("approval_flows.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    requester_id = Column(UUID(as_uuid=True),  nullable=False)
    status = Column(String(20), default="pending") # pending / approved / rejected / escalated / in_progress
    current_step_id = Column(UUID(as_uuid=True), ForeignKey("approval_steps.id", ondelete="SET NULL"))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    final_decision = Column(String(20))  
    comments = Column(Text)

class ApprovalAssignment(TenantBase, TenantScopedMixin):
    __tablename__ = "approval_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("approval_instances.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("approval_steps.id", ondelete="CASCADE"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), default="pending") # pending / approved / rejected
    assigned_at = Column(DateTime, default=datetime.utcnow)
    due_at = Column(DateTime)
    decided_at = Column(DateTime)
    comments = Column(Text)
    delegated_from = Column(UUID(as_uuid=True), ForeignKey("users.id"))

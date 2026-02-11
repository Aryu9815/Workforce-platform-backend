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


class AuditLog(TenantBase, TenantScopedMixin):
    """Audit trail for system operations."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True),  nullable=True)
    impersonated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=False)
    before_state = Column(JSONB, nullable=True)
    after_state = Column(JSONB, nullable=True)
    changes = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(100), nullable=True)
    request_id = Column(String(100), nullable=True)
    metadata_ = Column('metadata', JSONB, nullable=True)


class DomainEvent(TenantBase, TenantScopedMixin):
    """Event store for domain events."""
    __tablename__ = "domain_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSONB, nullable=False)
    metadata_ = Column('metadata' ,JSONB, nullable=True)
    correlation_id = Column(String(100), nullable=True)
    causation_id = Column(UUID(as_uuid=True), nullable=True)
    published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

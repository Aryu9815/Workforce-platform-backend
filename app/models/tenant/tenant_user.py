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
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class TenantUser(TenantBase, TenantScopedMixin):
    """Junction table for users and tenants."""
    __tablename__ = "tenant_users"
    tenant_uuid = Column(PG_UUID(as_uuid=True), nullable=False)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_by = Column(UUID(as_uuid=True), nullable=True)
    is_primary = Column(Boolean, default=False)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    settings = Column(JSONB, default=dict)
    
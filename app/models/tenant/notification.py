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
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, JSONB, INET
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.sql import func

from app.db.db_connection import TenantBase


class Notifications(TenantBase):
    """Audit trail for system operations."""
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True),  nullable=False)
    tenant_id = Column(UUID(as_uuid=True),  nullable=False)
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=True)
    entity_id = Column(UUID(as_uuid=True),  nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

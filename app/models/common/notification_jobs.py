
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

from app.db.db_connection import CommonBase

class NotificationJobs(CommonBase):
    """Event store for domain events."""
    __tablename__ = "notification_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True),  nullable=False)
    tenant_id = Column(UUID(as_uuid=True),  nullable=False)
    channel = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(100), default="pending", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
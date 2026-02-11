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

class File(TenantBase, TenantScopedMixin):
    """File storage records."""
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_name = Column(String(255), nullable=False)
    storage_key = Column(String(500), unique=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    extension = Column(String(20), nullable=True)
    checksum = Column(String(64), nullable=True)
    storage_provider = Column(String(20), default="s3")
    bucket_name = Column(String(100), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    is_public = Column(Boolean, default=False)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column('metadata',JSONB, default=dict)


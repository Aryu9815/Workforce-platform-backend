import uuid
from sqlalchemy import (
    Column, String, DateTime, Integer, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.db_connection import CommonBase
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

class User(CommonBase):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    salt = Column(String(255), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="active")
    tenant_ids = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

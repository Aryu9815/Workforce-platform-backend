import uuid
from sqlalchemy import Column, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.db_connection import TenantScopedMixin, TenantBase

class TenantUser(TenantBase, TenantScopedMixin):
    """Junction table for users and tenants."""
    __tablename__ = "tenant_users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_by = Column(UUID(as_uuid=True), nullable=True)
    is_primary = Column(Boolean, default=False)
    department_id = Column(UUID(as_uuid=True), nullable=True)
    settings = Column(JSONB, default=dict)
    
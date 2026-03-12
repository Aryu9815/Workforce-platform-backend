import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, ForeignKey, 
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.db_connection import TenantScopedMixin, TenantBase
from app.core.constants import ROLE_ID


class Permission(TenantBase, TenantScopedMixin):
    """System permissions model."""
    __tablename__ = "permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    resource = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    is_system = Column(Boolean, default=False)


class Role(TenantBase, TenantScopedMixin):
    """Role definitions per tenant."""
    __tablename__ = "roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)


class RolePermission(TenantBase, TenantScopedMixin):
    """Many-to-many linking roles to permissions."""
    __tablename__ = "role_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey(ROLE_ID, ondelete="CASCADE"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    conditions = Column(JSONB, nullable=True)


class TenantUserRole(TenantBase, TenantScopedMixin):
    """Assigns roles to users within tenant context."""
    __tablename__ = "tenant_user_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey(ROLE_ID, ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=True)  # Will be FK to projects
    assigned_by = Column(UUID(as_uuid=True), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)



class FieldPermission(TenantBase, TenantScopedMixin):
    """Field-level permission definitions."""
    __tablename__ = "field_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey(ROLE_ID, ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    permission = Column(String(20), nullable=False)  # read, write, hidden
    conditions = Column(JSONB, nullable=True)
    

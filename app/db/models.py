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


class TimestampMixin:
    """Mixin for timestamp columns."""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None

# ============================================
# Core Platform Models
# ============================================

class Tenant(Base, TimestampMixin):
    """Tenant/Organization model."""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC")
    status = Column(String(20), default="active")
    settings = Column(JSONB, default=dict)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    users = relationship("TenantUser", back_populates="tenant")
    roles = relationship("Role", back_populates="tenant")
    departments = relationship("Department", back_populates="tenant")


class User(Base, TimestampMixin, SoftDeleteMixin):
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
    
    # Relationships
    tenant_users = relationship("TenantUser", foreign_keys="[TenantUser.user_id]", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class TenantUser(Base, TimestampMixin):
    """Junction table for users and tenants."""
    __tablename__ = "tenant_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_primary = Column(Boolean, default=False)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    settings = Column(JSONB, default=dict)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    user = relationship("User", back_populates="tenant_users", foreign_keys=[user_id])
    
    __table_args__ = (UniqueConstraint("tenant_id", "user_id"),)


class RefreshToken(Base):
    """Refresh token model for JWT session management."""
    __tablename__ = "refresh_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    token = Column(String(255), unique=True, nullable=False)
    refresh_token = Column(String(255), unique=True, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")


# ============================================
# RBAC Models
# ============================================

class Permission(Base):
    """System permissions model."""
    __tablename__ = "permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    resource = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission")


class Role(Base, TimestampMixin, SoftDeleteMixin):
    """Role definitions per tenant."""
    __tablename__ = "roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="roles")
    role_permissions = relationship("RolePermission", back_populates="role")
    user_roles = relationship("TenantUserRole", back_populates="role")
    
    __table_args__ = (UniqueConstraint("tenant_id", "name"),)


class RolePermission(Base):
    """Many-to-many linking roles to permissions."""
    __tablename__ = "role_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    conditions = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)


class TenantUserRole(Base):
    """Assigns roles to users within tenant context."""
    __tablename__ = "tenant_user_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=True)  # Will be FK to projects
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="user_roles")
    
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", "role_id", "project_id"),)


class FieldPermission(Base):
    """Field-level permission definitions."""
    __tablename__ = "field_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    permission = Column(String(20), nullable=False)  # read, write, hidden
    conditions = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint("tenant_id", "role_id", "entity_type", "field_name"),)


# ============================================
# Staffing Models
# ============================================

class Department(Base, TimestampMixin, SoftDeleteMixin):
    """Department model."""
    __tablename__ = "departments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    head_id = Column(UUID(as_uuid=True), nullable=True)  # Will be FK to staff_profiles
    is_active = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="departments")


class Designation(Base, TimestampMixin):
    """Designation/Job title model."""
    __tablename__ = "designations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


class StaffProfile(Base, TimestampMixin, SoftDeleteMixin):
    """Staff profile model."""
    __tablename__ = "staff_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    employee_code = Column(String(50), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    designation_id = Column(UUID(as_uuid=True), ForeignKey("designations.id", ondelete="RESTRICT"), nullable=False)
    reporting_manager_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    employment_type = Column(String(20), nullable=False)  # full_time, contractor, vendor
    join_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=True)
    exit_reason = Column(String(100), nullable=True)
    work_location = Column(String(100), nullable=True)
    skills = Column(JSONB, default=list)
    certifications = Column(JSONB, default=list)
    emergency_contact = Column(JSONB, nullable=True)
    documents = Column(JSONB, default=list)
    custom_fields = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (UniqueConstraint("tenant_id", "employee_code"),)


class StaffAssignment(Base, TimestampMixin):
    """Staff project assignments."""
    __tablename__ = "staff_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)  # Will be FK to projects
    role = Column(String(100), nullable=True)
    allocation_percentage = Column(Integer, default=100)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_primary = Column(Boolean, default=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


# ============================================
# Attendance Models
# ============================================

class AttendancePolicy(Base, TimestampMixin):
    """Attendance policy configuration."""
    __tablename__ = "attendance_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    work_hours_per_day = Column(Numeric(4, 2), default=8.0)
    work_days_per_week = Column(Integer, default=5)
    grace_period_minutes = Column(Integer, default=15)
    overtime_threshold = Column(Numeric(4, 2), default=8.0)
    overtime_calculation = Column(String(20), default="daily")
    is_default = Column(Boolean, default=False)
    rules = Column(JSONB, default=dict)


class Shift(Base):
    """Work shift definition."""
    __tablename__ = "shifts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    break_duration_minutes = Column(Integer, default=60)
    days_of_week = Column(ARRAY(Integer), nullable=False)
    is_night_shift = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AttendanceRecord(Base, TimestampMixin):
    """Daily attendance records."""
    __tablename__ = "attendance_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    check_in = Column(DateTime(timezone=True), nullable=True)
    check_out = Column(DateTime(timezone=True), nullable=True)
    check_in_location = Column(JSONB, nullable=True)
    check_out_location = Column(JSONB, nullable=True)
    check_in_method = Column(String(20), nullable=True)
    check_out_method = Column(String(20), nullable=True)
    work_hours = Column(Numeric(5, 2), nullable=True)
    overtime_hours = Column(Numeric(5, 2), default=0)
    status = Column(String(20), default="present")  # present, absent, late, half_day
    notes = Column(Text, nullable=True)
    is_manual_entry = Column(Boolean, default=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    __table_args__ = (UniqueConstraint("tenant_id", "staff_id", "date"),)


class LeaveType(Base):
    """Leave type definitions."""
    __tablename__ = "leave_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    is_paid = Column(Boolean, default=True)
    color = Column(String(7), nullable=True)
    requires_approval = Column(Boolean, default=True)
    max_days_per_year = Column(Integer, nullable=True)
    carry_forward = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LeaveRequest(Base, TimestampMixin):
    """Leave requests from staff."""
    __tablename__ = "leave_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id", ondelete="RESTRICT"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_requested = Column(Numeric(4, 1), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="pending")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    documents = Column(JSONB, default=list)


class Holiday(Base):
    """Company holidays."""
    __tablename__ = "holidays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(20), default="public")
    is_recurring = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# Project & Task Models
# ============================================

class Workflow(Base, TimestampMixin, SoftDeleteMixin):
    """Workflow definitions."""
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    entity_type = Column(String(50), nullable=False)
    is_default = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    settings = Column(JSONB, default=dict)


class WorkflowState(Base):
    """Workflow state definitions."""
    __tablename__ = "workflow_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WorkflowTransitions(Base):
    """Workflow state definitions."""
    __tablename__ = "workflow_transitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    from_state_id = Column(UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False)
    to_state_id = Column(UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    request_approval = Column(Boolean, default=False)
    approval_flow_id = Column(UUID(as_uuid=True), ForeignKey("approval_flows.id", ondelete="CASCADE"), nullable=False)
    auto_transition = Column(Boolean, default=False)
    condition_rules = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TransitionsRules(Base):
    """Workflow state definitions."""
    __tablename__ = "transition_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    transition_id = Column(UUID(as_uuid=True), ForeignKey("workflow_transitions.id", ondelete="CASCADE"), nullable=False)
    rule_type = Column(String(50), nullable=False)
    rule_config = Column(JSONB, nullable=False)
    error_message = Column(String(255), nullable=True)

class Status(Base):
    """Status definitions for entities."""
    __tablename__ = "statuses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    entity_type = Column(String(50), nullable=False, index=True)
    color = Column(String(7), nullable=False)
    icon = Column(String(50), nullable=True)
    order_index = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Project(Base, TimestampMixin, SoftDeleteMixin):
    """Project model."""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="planning")
    priority = Column(String(20), default="medium")
    project_type = Column(String(50), nullable=True)
    parent_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    project_manager_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="RESTRICT"), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    budget = Column(Numeric(15, 2), nullable=True)
    cost_estimate = Column(Numeric(15, 2), nullable=True)
    actual_cost = Column(Numeric(15, 2), default=0)
    currency = Column(String(3), default="USD")
    progress_percentage = Column(Integer, default=0)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    location = Column(JSONB, nullable=True)
    settings = Column(JSONB, default=dict)
    custom_fields = Column(JSONB, default=dict)
    is_template = Column(Boolean, default=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)


class ProjectMember(Base, TenantMixin, SoftDeleteMixin, TimestampMixin):
    """Project membership."""
    __tablename__ = "project_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(100), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    permissions = Column(JSONB, default=list)
    is_removed = Column(Boolean, default=False)


class Task(Base, TenantMixin, TimestampMixin, SoftDeleteMixin):
    """Task model."""
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status_id = Column(UUID(as_uuid=True), ForeignKey("statuses.id", ondelete="SET NULL"), nullable=True)
    priority = Column(String(20), default="medium")
    task_type = Column(String(50), nullable=True)
    estimated_hours = Column(Numeric(6, 2), nullable=True)
    actual_hours = Column(Numeric(6, 2), default=0)
    estimated_cost = Column(Numeric(12, 2), nullable=True)
    actual_cost = Column(Numeric(12, 2), default=0)
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    progress_percentage = Column(Integer, default=0)
    milestone = Column(Boolean, default=False)
    billable = Column(Boolean, default=True)
    location = Column(JSONB, nullable=True)
    custom_fields = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)


class TaskAssignee(Base):
    """Task assignees."""
    __tablename__ = "task_assignees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=False)
    allocation_percentage = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint("tenant_id", "task_id", "staff_id"),)


class TaskDependency(Base):
    """Task dependencies."""
    __tablename__ = "task_dependencies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String(20), default="finish_to_start")
    lag_days = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint("tenant_id", "task_id", "depends_on_task_id"),)


class TaskComment(Base):
    """Task comments."""
    __tablename__ = "task_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("task_comments.id", ondelete="CASCADE"), nullable=True)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# Financial Models
# ============================================

class ExpenseCategory(Base):
    """Expense categories for reimbursements."""
    __tablename__ = "expense_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True)
    requires_receipt = Column(Boolean, default=True)
    max_amount = Column(Numeric(12, 2), nullable=True)
    tax_deductible = Column(Boolean, default=False)
    gl_account_code = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReimbursementClaim(Base, TimestampMixin):
    """Reimbursement claims."""
    __tablename__ = "reimbursement_claims"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    claim_number = Column(String(50), unique=True, nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    claim_date = Column(Date, nullable=False)
    expense_date_start = Column(Date, nullable=True)
    expense_date_end = Column(Date, nullable=True)
    total_amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD")
    exchange_rate = Column(Numeric(10, 6), default=1)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="draft")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    gl_exported = Column(Boolean, default=False)
    gl_exported_at = Column(DateTime(timezone=True), nullable=True)
    custom_fields = Column(JSONB, default=dict)


class ReimbursementItem(Base):
    """Individual items in a reimbursement claim."""
    __tablename__ = "reimbursement_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("reimbursement_claims.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("expense_categories.id", ondelete="RESTRICT"), nullable=False)
    expense_date = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Numeric(8, 2), default=1)
    unit_price = Column(Numeric(12, 2), nullable=True)
    tax_amount = Column(Numeric(12, 2), default=0)
    merchant_name = Column(String(255), nullable=True)
    merchant_location = Column(String(255), nullable=True)
    receipt_file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    is_billable = Column(Boolean, default=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    custom_fields = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# Inventory Models
# ============================================

class InventoryCategory(Base):
    """Inventory item categories."""
    __tablename__ = "inventory_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("inventory_categories.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InventoryLocation(Base):
    """Inventory storage locations."""
    __tablename__ = "inventory_locations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    location_type = Column(String(50), nullable=False)
    address = Column(JSONB, nullable=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InventoryItem(Base, TimestampMixin, SoftDeleteMixin):
    """Inventory items/SKUs."""
    __tablename__ = "inventory_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("inventory_categories.id", ondelete="RESTRICT"), nullable=False)
    unit_of_measure = Column(String(50), nullable=False)
    barcode = Column(String(100), nullable=True)
    manufacturer = Column(String(100), nullable=True)
    model_number = Column(String(100), nullable=True)
    cost_price = Column(Numeric(12, 2), nullable=True)
    selling_price = Column(Numeric(12, 2), nullable=True)
    reorder_level = Column(Integer, default=0)
    reorder_quantity = Column(Integer, default=0)
    is_trackable = Column(Boolean, default=True)
    is_consumable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    custom_fields = Column(JSONB, default=dict)
    
    __table_args__ = (UniqueConstraint("tenant_id", "sku"),)


class InventoryStock(Base, TimestampMixin):
    """Inventory stock levels per location."""
    __tablename__ = "inventory_stock"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("inventory_locations.id", ondelete="CASCADE"), nullable=False)
    quantity_on_hand = Column(Integer, default=0)
    quantity_reserved = Column(Integer, default=0)
    average_cost = Column(Numeric(12, 2), nullable=True)
    last_movement_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (UniqueConstraint("tenant_id", "item_id", "location_id"),)


class InventoryTransaction(Base, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Inventory transaction history."""
    __tablename__ = "inventory_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_number = Column(String(50), unique=True, nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("inventory_locations.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(String(30), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 2), nullable=True)
    total_cost = Column(Numeric(15, 2), nullable=True)
    reference_type = Column(String(50), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# Approvals Models
# ============================================

class ApprovalFlow(Base, TenantMixin,TimestampMixin, SoftDeleteMixin):
    __tablename__ = "approval_flows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    entity_type = Column(String(50), nullable=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    conditions = Column(JSONB)  # auto-assignment rules

class ApprovalStep(Base,TenantMixin, TimestampMixin, SoftDeleteMixin):
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
    

class ApprovalInstance(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "approval_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("approval_flows.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    requester_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending") # pending / approved / rejected / escalated / in_progress
    current_step_id = Column(UUID(as_uuid=True), ForeignKey("approval_steps.id", ondelete="SET NULL"))
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    final_decision = Column(String(20))  
    comments = Column(Text)

class ApprovalAssignment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "approval_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    instance_id = Column(UUID(as_uuid=True), ForeignKey("approval_instances.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("approval_steps.id", ondelete="CASCADE"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending") # pending / approved / rejected
    assigned_at = Column(DateTime, default=datetime.utcnow)
    due_at = Column(DateTime)
    decided_at = Column(DateTime)
    comments = Column(Text)
    delegated_from = Column(UUID(as_uuid=True), ForeignKey("users.id"))

# ============================================
# File Management Models
# ============================================

class File(Base):
    """File storage records."""
    __tablename__ = "files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    original_name = Column(String(255), nullable=False)
    storage_key = Column(String(500), unique=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    extension = Column(String(20), nullable=True)
    checksum = Column(String(64), nullable=True)
    storage_provider = Column(String(20), default="s3")
    bucket_name = Column(String(100), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    is_public = Column(Boolean, default=False)
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column('metadata',JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)


# ============================================
# Audit & Event Models
# ============================================

class AuditLog(Base):
    """Audit trail for system operations."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DomainEvent(Base):
    """Event store for domain events."""
    __tablename__ = "domain_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSONB, nullable=False)
    metadata_ = Column('metadata' ,JSONB, nullable=True)
    correlation_id = Column(String(100), nullable=True)
    causation_id = Column(UUID(as_uuid=True), nullable=True)
    published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

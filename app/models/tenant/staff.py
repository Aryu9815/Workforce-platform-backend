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


class Department(TenantBase, TenantScopedMixin):
    """Department model."""
    __tablename__ = "departments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    head_id = Column(UUID(as_uuid=True), nullable=True)  # Will be FK to staff_profiles


class Designation(TenantBase, TenantScopedMixin):
    """Designation/Job title model."""
    __tablename__ = "designations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    level = Column(Integer, nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)


class StaffProfile(TenantBase, TenantScopedMixin):
    """Staff profile model."""
    __tablename__ = "staff_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
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
    

class StaffAssignment(TenantBase, TenantScopedMixin):
    """Staff project assignments."""
    __tablename__ = "staff_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)  # Will be FK to projects
    role = Column(String(100), nullable=True)
    allocation_percentage = Column(Integer, default=100)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_primary = Column(Boolean, default=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

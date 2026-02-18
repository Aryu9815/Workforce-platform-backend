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


class AssetCategory(TenantBase, TenantScopedMixin):
    __tablename__ = "asset_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, unique=True)
    description = Column(Text, nullable=True)
class AssetType(TenantBase, TenantScopedMixin):
    __tablename__ = "asset_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asset_categories.id", ondelete="RESTRICT"),
        nullable=False
    )

    name = Column(String(150), nullable=False)
    brand = Column(String(100), nullable=True)
    model_number = Column(String(100), nullable=True)

    is_serialized = Column(Boolean, default=True)
    # True → track individual units (laptop, phone)
    # False → bulk tracking (chair, cable)

    purchase_cost = Column(Numeric(12,2), nullable=True)
    warranty_months = Column(Integer, nullable=True)

    description = Column(Text, nullable=True)
class Asset(TenantBase, TenantScopedMixin):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    asset_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asset_types.id", ondelete="RESTRICT"),
        nullable=False
    )

    asset_tag = Column(String(100), nullable=False, unique=True)
    serial_number = Column(String(150), nullable=True)

    status = Column(
        String(30),
        default="available"
    )
    # available
    # assigned
    # maintenance
    # lost
    # disposed

    purchase_date = Column(Date, nullable=True)
    purchase_price = Column(Numeric(12,2), nullable=True)

    location = Column(String(150), nullable=True)

    notes = Column(Text, nullable=True)
class AssetAssignment(TenantBase, TenantScopedMixin):
    __tablename__ = "asset_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False
    )

    staff_id = Column(
        UUID(as_uuid=True),
        ForeignKey("staff_profiles.id", ondelete="RESTRICT"),
        nullable=False
    )

    assigned_date = Column(Date, nullable=False)
    expected_return_date = Column(Date, nullable=True)
    returned_date = Column(Date, nullable=True)

    condition_on_assign = Column(String(50), nullable=True)
    condition_on_return = Column(String(50), nullable=True)

    is_active = Column(Boolean, default=True)

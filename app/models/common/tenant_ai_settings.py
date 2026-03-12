"""
Tenant AI Settings model for configuring AI provider per tenant.
"""

import uuid
from sqlalchemy import Column, String, Boolean, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.sql import func

from app.db.db_connection import CommonBase


class TenantAISettings(CommonBase):
    """Stores AI configuration for each tenant."""

    __tablename__ = "tenant_ai_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    provider = Column(String(50), nullable=False)   # openai / ollama
    model = Column(String(100), nullable=False)

    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1024)

    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            name="uq_tenant_ai_provider"
        ),
        Index("idx_tenant_ai_settings_tenant", "tenant_id"),
    )
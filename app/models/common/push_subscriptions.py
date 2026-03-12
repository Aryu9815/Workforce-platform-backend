# app/models/push_subscription.py
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.db_connection import CommonBase
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, JSONB, INET
import uuid

class PushSubscription(CommonBase):
    __tablename__ = "push_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    endpoint = Column(String, nullable=False)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
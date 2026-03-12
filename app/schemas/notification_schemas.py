
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from enum import Enum
from pydantic import field_validator
from app.schemas.validators import (
    validate_description,
    validate_name_field,
    validate_optional_str,
    validate_positive_number,
)
from app.schemas.base_schema import BaseSchema


class NotificationChannel(str, Enum):
    """Notification channel enum."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class ProjectPriority(str, Enum):
    """Project priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationBase(BaseSchema):
    """Base notification schema."""
    tenant_id: UUID
    user_id: UUID
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    is_read: Optional[bool] = False

    @field_validator("title")
    def validate_title(cls, value):
        return validate_name_field(value, max_length=255, field="title")

    @field_validator("message")
    def validate_message(cls, value):
        return validate_description(
            value,
            max_length=2000,
            is_optional=False,
            field="message",
        )

    @field_validator("entity_type")
    def validate_entity_type(cls, value):
        return validate_optional_str(
            value,
            max_length=100,
            field="entity_type",
        )


class NotificationCreate(NotificationBase):
    """Notification creation schema."""
    pass

class NotificationUpdate(BaseSchema):
    """Notification update schema."""
    is_read: bool

class NotificationJobBase(BaseSchema):
    """Base notification job schema."""
    notification_id: UUID
    channel: NotificationChannel
    payload: Dict[str, Any]
    status: Optional[str] = "pending"
    attempts: Optional[int] = 0

    @field_validator("status")
    def validate_status(cls, value):
        return validate_optional_str(
            value,
            max_length=50,
            field="status",
        )

    @field_validator("attempts")
    def validate_attempts(cls, value):
        # attempts is a non-negative integer
        return validate_positive_number(
            value,
            field="attempts",
            is_optional=True,
            strictly_positive=False,
        )

class NotificationJobCreate(NotificationJobBase):
    """Notification job creation schema."""
    pass

class NotificationJobUpdate(BaseSchema):
    """Notification job update schema."""
    status: Optional[str] = None
    attempts: Optional[int] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None

class NotificationResponse(BaseSchema):
    """Notification response schema."""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    is_read: Optional[bool] = False
    created_at: datetime
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import EmailStr
from app.schemas.base_schema import BaseSchema, TimestampSchema


class UserBase(BaseSchema):
    """Base user schema."""
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None

class UserResponse(UserBase, TimestampSchema):
    """User response schema."""
    id: UUID
    avatar_url: Optional[str] = None
    last_login_at: Optional[datetime] = None
    status: str
    full_name: str
    staff_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None

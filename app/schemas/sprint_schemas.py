
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)

class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SprintStatus(str, Enum):
    """Task priority enum."""
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SprintBase(BaseSchema):
    """Base task schema."""
    name: str = Field(..., min_length=1, max_length=500)
    goal: Optional[str] = None
    status: SprintStatus = SprintStatus.PLANNED
    capacity: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SprintCreate(SprintBase):
    """Task creation schema."""
    project_id: UUID


class SprintUpdate(BaseSchema):
    """Task update schema."""
    name: Optional[str] = None
    goal: Optional[str] = None
    status: Optional[SprintStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    capacity: Optional[int] = None


class SprintResponse(SprintBase, TimestampSchema):
    """Task response schema."""
    id: UUID
    project_id: UUID
    created_by: UUID
    updated_by: Optional[UUID] = None
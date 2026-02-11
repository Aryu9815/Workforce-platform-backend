

"""
Pydantic schemas for API request/response validation.
"""
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
    
class DepartmentBase(BaseSchema):
    """Base department schema."""
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None


class DepartmentCreate(DepartmentBase):
    """Department creation schema."""
    pass



class DepartmentUpdate(BaseSchema):
    """Department update schema."""
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase, TimestampSchema):
    """Department response schema."""
    id: UUID
    head_id: Optional[UUID] = None
    is_active: bool
    staff_count: int = 0

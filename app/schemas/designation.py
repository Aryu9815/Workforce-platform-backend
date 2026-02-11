
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

class DesignationCreate(BaseModel):
    name: str
    level: Optional[int] = None
    department_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: bool = True


class DesignationUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    department_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DesignationResponse(BaseModel):
    id: UUID
    name: str
    level: Optional[int] = None
    department_id: Optional[UUID] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

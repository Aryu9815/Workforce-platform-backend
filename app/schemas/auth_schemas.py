"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum
from pydantic import EmailStr, field_validator
from app.utils.schema_uitls import NormalizedEmailStr

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseSchema):
    """Token response schema."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    tenant: Optional[Dict[str, Any]] = None
    multiple_tenants_found: bool = False


class LoginRequest(BaseSchema):
    """Login request schema."""
    email: NormalizedEmailStr
    password: str

    
class RegisterRequest(BaseSchema):
    """Registration request schema."""
    email: NormalizedEmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None


class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema."""
    refresh_token: str


class ChangePasswordRequest(BaseSchema):
    """Change password request schema."""
    current_password: str
    new_password: str = Field(..., min_length=8)


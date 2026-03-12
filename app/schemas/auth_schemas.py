"""
Pydantic schemas for API request/response validation.
"""
from typing import Optional, List, Dict, Any
from pydantic import Field
from pydantic import field_validator
from app.utils.schema_uitls import NormalizedEmailStr
from app.schemas.base_schema import BaseSchema
from app.schemas.validators import (
    validate_name_field,
    validate_phone_number
)


class TokenResponse(BaseSchema):
    """Token response schema."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    tenant: Optional[Dict[str, Any]] = None
    multiple_tenants_found: bool = False
    permissions: List[str] = []


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

    @field_validator("first_name", "last_name")
    def validate_names(cls, value, info):
        return validate_name_field(
            value,
            max_length=100,
            field=info.field_name,
            only_letters=True,
        )

    @field_validator("phone")
    def validate_phone(cls, value):
        return validate_phone_number(value, is_optional=True)

class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema."""
    refresh_token: str


class ChangePasswordRequest(BaseSchema):
    """Change password request schema."""
    current_password: str
    new_password: str = Field(..., min_length=8)


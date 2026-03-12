
from typing import Optional, List
from pydantic import Field, field_validator
from app.schemas.base_schema import BaseSchema
from app.schemas.validators import (
    validate_name_field,
    validate_optional_str
)


class RoleBase(BaseSchema):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_system: bool = False
    is_default: bool = False



    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value, max_length=255, field="name", only_letters=True)

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=1000,
            field="description",
        )
    
class RoleCreate(RoleBase):
    """Project creation schema."""
    pass

class RoleUpdate(BaseSchema):
    """Project update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_system: Optional[bool] = None
    is_default: Optional[bool] = None
    permissions: Optional[List[str]] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=255,
            field="name",
            is_optional=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=1000,
            field="description",
        )
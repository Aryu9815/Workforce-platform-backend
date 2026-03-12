from uuid import UUID
from datetime import date
from typing import Optional, List
from pydantic import Field, field_validator
from app.schemas.base_schema import BaseSchema
from app.schemas.validators import (
    validate_code_field,
    validate_date_ymd,
    validate_description,
    validate_name_field,
    validate_optional_str,
    validate_positive_number,
)

# ===============================
# Asset Category
# ===============================

class AssetCategoryCreate(BaseSchema):
    name: str
    code: str 
    description: Optional[str] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value)

    @field_validator("code")
    def validate_code(cls, value):
        return validate_code_field(value)

    @field_validator("description")
    def validate_description(cls, value):
        return validate_description(value, is_optional=True)



class AssetCategoryUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value, is_optional=True)

    @field_validator("description")
    def validate_description(cls, value):
        return validate_description(value, is_optional=True)
    
# ===============================
# Asset Type
# ===============================

class AssetTypeCreate(BaseSchema):
    category_id: UUID
    name: str = Field(..., min_length=1, max_length=150)
    brand: Optional[str] = Field(None, max_length=100)
    model_number: Optional[str] = Field(None, max_length=100)
    is_serialized: bool = True
    tag_prefix: str = Field(None, max_length=10)
    warranty_months: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value)

    @field_validator("description")
    def validate_description(cls, value):
        return validate_description(value, is_optional=True)
    
    @field_validator("brand")
    def validate_brand(cls, value):
        return validate_name_field(value, max_length=100, field="brand", is_optional=True)

    @field_validator("model_number")
    def validate_model_number(cls, value):
        return validate_code_field(value, max_length=100, field="model_number", is_optional=True)



    @field_validator("warranty_months")
    def validate_warranty_months(cls, value):
        return validate_positive_number(
            value,
            field="warranty_months",
            is_optional=True,
            strictly_positive=True,
        )
    
class AssetTypeUpdate(BaseSchema):
    name: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    warranty_months: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(value, is_optional=True)

    @field_validator("brand")
    def validate_brand(cls, value):
        return validate_name_field(
            value,
            max_length=100,
            field="brand",
            is_optional=True,
        )

    @field_validator("model_number")
    def validate_model_number(cls, value):
        return validate_code_field(
            value,
            max_length=100,
            field="model_number",
            is_optional=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(value, max_length=500, field="description")

    @field_validator("purchase_cost")
    def validate_purchase_cost(cls, value):
        return validate_positive_number(
            value,
            field="purchase_cost",
            is_optional=True,
            strictly_positive=True,
        )

    @field_validator("warranty_months")
    def validate_warranty_months(cls, value):
        return validate_positive_number(
            value,
            field="warranty_months",
            is_optional=True,
            strictly_positive=True,
        )

# ===============================
# Asset Unit
# ===============================

class AssetCreate(BaseSchema):
    asset_type_id: UUID
    # asset_tag: str = Field(..., min_length=1, max_length=100)
    quantity: Optional[int] = 1
    serial_numbers: Optional[List[str]] = None
    purchase_date: Optional[date]
    purchase_price: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=150)
    notes: Optional[str] = None

    @field_validator("serial_numbers")
    def validate_serial_numbers(cls, value):
        if value is None:
            return value
        return [
            validate_code_field(
                sn,
                field="serial_number",
                max_length=100,
                is_optional=False,
            )
            for sn in value
        ]

    @field_validator("purchase_date", mode="before")
    def validate_purchase_date(cls, value):
        return validate_date_ymd(value, field="purchase_date", is_optional=True)

    @field_validator("purchase_price")
    def validate_purchase_price(cls, value):
        return validate_positive_number(
            value,
            field="purchase_price",
            is_optional=True,
            strictly_positive=True,
        )

    @field_validator("location")
    def validate_location(cls, value):
        return validate_optional_str(value, max_length=150, field="location")

    @field_validator("notes")
    def validate_notes(cls, value):
        return validate_optional_str(value, max_length=1000, field="notes")

class AssetUpdate(BaseSchema):
    status: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("location")
    def validate_location(cls, value):
        return validate_optional_str(value, max_length=150, field="location")

    @field_validator("notes")
    def validate_notes(cls, value):
        return validate_optional_str(value, max_length=1000, field="notes")


# ===============================
# Assignment
# ===============================

class AssetAssignRequest(BaseSchema):
    staff_id: UUID
    assigned_date: date
    expected_return_date: Optional[date] = None
    condition_on_assign: Optional[str] = None

    @field_validator("assigned_date", mode="before")
    def validate_assigned_date(cls, value):
        return validate_date_ymd(value, field="assigned_date", is_optional=False)

    @field_validator("expected_return_date", mode="before")
    def validate_expected_return_date(cls, value):
        return validate_date_ymd(
            value,
            field="expected_return_date",
            is_optional=True,
        )

    @field_validator("condition_on_assign")
    def validate_condition_on_assign(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="condition_on_assign",
        )
from pydantic import BaseModel
class AssignmentHistoryItem(BaseModel):
    id: UUID
    staff_id: UUID
    staff_name: str
    assigned_date: date
    expected_return_date: Optional[date]
    returned_date: Optional[date]
    condition_on_assign: Optional[str]
    condition_on_return: Optional[str]
    is_active: bool


class AssetHistoryResponse(BaseModel):
    id: UUID
    asset_tag: str
    serial_number: Optional[str]
    status: str
    location: Optional[str]
    purchase_date: Optional[date]
    purchase_price: Optional[float]

    asset_type: dict
    category: dict

    total_assignments: int
    current_assignment: Optional[AssignmentHistoryItem]
    assignment_history: List[AssignmentHistoryItem]
class AssetReturnRequest(BaseSchema):
    returned_date: date
    condition_on_return: Optional[str] = None

    @field_validator("returned_date", mode="before")
    def validate_returned_date(cls, value):
        return validate_date_ymd(value, field="returned_date", is_optional=False)

    @field_validator("condition_on_return")
    def validate_condition_on_return(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="condition_on_return",
        )

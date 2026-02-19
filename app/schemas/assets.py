from uuid import UUID
from datetime import date, datetime
from typing import Optional , List
from pydantic import Field
from app.api.schemas import BaseSchema, TimestampSchema


# ===============================
# Asset Category
# ===============================

class AssetCategoryCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = None


class AssetCategoryUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ===============================
# Asset Type
# ===============================

class AssetTypeCreate(BaseSchema):
    category_id: UUID
    name: str = Field(..., min_length=1, max_length=150)
    brand: Optional[str] = Field(None, max_length=100)
    model_number: Optional[str] = Field(None, max_length=100)
    is_serialized: bool = True
    purchase_cost: Optional[float] = Field(None, ge=0)
    warranty_months: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None


class AssetTypeUpdate(BaseSchema):
    name: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    purchase_cost: Optional[float] = Field(None, ge=0)
    warranty_months: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ===============================
# Asset Unit
# ===============================

class AssetCreate(BaseSchema):
    asset_type_id: UUID
    # asset_tag: str = Field(..., min_length=1, max_length=100)
    quantity: Optional[int] = 1
    serial_numbers:  Optional[List[str]] =None
    purchase_date: Optional[date]
    purchase_price: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=150)
    notes: Optional[str] = None


class AssetUpdate(BaseSchema):
    status: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# ===============================
# Assignment
# ===============================

class AssetAssignRequest(BaseSchema):
    staff_id: UUID
    assigned_date: date
    expected_return_date: Optional[date] = None
    condition_on_assign: Optional[str] = None


class AssetReturnRequest(BaseSchema):
    returned_date: date
    condition_on_return: Optional[str] = None

"""
Asset management API routes.
ERP-grade asset tracking with assignment workflow.
"""
from sqlalchemy import select, desc
import re
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.db.base import get_db_session
from app.services.crud import CRUDService
from app.core.logging_config import get_logger

from app.models.tenant import (
    AssetCategory,
    AssetType,
    Asset,
    AssetAssignment,
    StaffProfile,
)

from app.api.schemas import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from app.schemas.assets import (
    AssetCategoryCreate,
    AssetCategoryUpdate,
    AssetTypeCreate,
    AssetTypeUpdate,
    AssetCreate,
    AssetUpdate,
    AssetAssignRequest,
    AssetReturnRequest
)
from app.utils.rbac_middleware import require_permissions

logger = get_logger(__name__)
router = APIRouter(prefix="/assets", tags=["Asset Management"])

category_crud = CRUDService(AssetCategory)
type_crud = CRUDService(AssetType)
asset_crud = CRUDService(Asset)
assignment_crud = CRUDService(AssetAssignment)
staff_crud = CRUDService(StaffProfile)

# ============================================================
# Asset Categories
# ============================================================

@router.get("/categories", response_model=List[dict])
@require_permissions(["asset:view"])
async def list_asset_categories(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    categories = await category_crud.get_multi(db)

    return [
        {
            "id": str(cat.id),
            "name": cat.name,
            "code": cat.code,
            "description": cat.description,
        }
        for cat in categories
    ]


@router.post("/categories", response_model=dict, status_code=201)
@require_permissions(["asset:create"])
async def create_asset_category(
    request: Request,
    data: AssetCategoryCreate,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Unauthorized")

    existing = await category_crud.get_by_fields(
        db,
        fields={"code": data.code}
    )

    if existing:
        raise HTTPException(409, "Category code already exists")

    
    category = await category_crud.create(
        db,
        obj_in={
            **data.model_dump(),
            "created_by": str(user_id),
            "updated_by": str(user_id)
        }
    )

    await db.commit()
    await db.refresh(category)

    return {
        "id": str(category.id),
        "name": category.name,
        "code": category.code,
        "description": category.description,
    }



# ============================================================
# Asset Types
# ============================================================

@router.get("/types", response_model=List[dict])
@require_permissions(["asset:view"])
async def list_asset_types(
    request: Request,
    category_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    filters = {}
    if category_id:
        filters["category_id"] = category_id

    types = await type_crud.get_multi(db, filters=filters)

    return [
        {
            "id": str(t.id),
            "name": t.name,
            "brand": t.brand,
            "model_number": t.model_number,
            "category_id": str(t.category_id),
            "is_serialized": t.is_serialized,
        }
        for t in types
    ]


@router.post("/types", response_model=dict, status_code=201)
@require_permissions(["asset:create"])
async def create_asset_type(
    request: Request,
    data: AssetTypeCreate,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Unauthorized")
    category = await category_crud.get(db, data.category_id)
    if not category:
        raise HTTPException(404, "Asset category not found")

    asset_type = await type_crud.create(
        db,
        obj_in={
            **data.model_dump(),
            "created_by": str(user_id),
            "updated_by": str(user_id)
        }
    )

    await db.commit()

    return {
        "id": str(asset_type.id),
        "name": asset_type.name,
    }



# ============================================================
# Asset Units
# ============================================================

@router.get("", response_model=PaginatedResponse)
@require_permissions(["asset:view"])
async def list_assets(
    request: Request,
    pagination: PaginationParams = Depends(),
    asset_type_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    filters = {}
    if asset_type_id:
        filters["asset_type_id"] = asset_type_id
    if status:
        filters["status"] = status

    total = await asset_crud.count(db, filters=filters)

    assets = await asset_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    
    items = [
        {
            "id": str(a.id),
            "asset_tag": a.asset_tag,
            "serial_number": a.serial_number,
            "asset_type_id": str(a.asset_type_id),
            "status": a.status,
            "location": a.location,
            "purchase_date": a.purchase_date,
            "purchase_price": float(a.purchase_price) if a.purchase_price else None,
        }
        for a in assets
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


async def generate_asset_tags(
    db: AsyncSession,
    asset_type: AssetType,
    quantity: int
):
    prefix = asset_type.name[:3].upper()

    # Get latest asset_tag for this type
    stmt = (
        select(Asset.asset_tag)
        .where(Asset.asset_type_id == asset_type.id)
        .order_by(desc(Asset.asset_tag))
        .limit(1)
    )

    result = await db.execute(stmt)
    last_asset_tag = result.scalar_one_or_none()

    last_number = 0

    if last_asset_tag:
        match = re.search(r"(\d+)$", last_asset_tag)
        if match:
            last_number = int(match.group(1))

    return [
        f"{prefix}-{str(last_number + i).zfill(4)}"
        for i in range(1, quantity + 1)
    ]




@router.post("", response_model=dict, status_code=201)
@require_permissions(["asset:create"])
async def create_asset(
    request: Request,
    data: AssetCreate,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Unauthorized")

    asset_type = await type_crud.get(db, data.asset_type_id)
    if not asset_type:
        raise HTTPException(404, "Asset type not found")

    quantity = data.quantity or 1

    # ERP Rules
    
    if asset_type.is_serialized:
        if not data.serial_numbers:
            raise HTTPException(400, "Serial numbers required")

        if len(data.serial_numbers) != quantity:
            raise HTTPException(400, "Serial count must match quantity")
    if not asset_type.is_serialized and data.serial_numbers:
        raise HTTPException(400, "Bulk asset must not have serial number")

    asset_tags = await generate_asset_tags(
        db,
        asset_type,
        quantity
    )

    created_assets = []

    for i , tag in enumerate(asset_tags):
        asset = Asset(
            asset_type_id=data.asset_type_id,
            asset_tag=tag,
            serial_number=data.serial_numbers[i] ,
            purchase_date=data.purchase_date,
            purchase_price=data.purchase_price,
            location=data.location,
            notes=data.notes,
            status="available",
            created_by=str(user_id),
            updated_by=str(user_id)
        )

        db.add(asset)
        created_assets.append(tag)

    await db.commit()

    return {
        "message": f"{quantity} asset(s) created successfully",
        "asset_tags": created_assets
    }



# ============================================================
# Asset Assignment Workflow
# ============================================================

@router.post("/{asset_id}/assign", response_model=SuccessResponse)
@require_permissions(["asset:create"])
async def assign_asset(
    request: Request,
    asset_id: UUID,
    data: AssetAssignRequest,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "user_id", None)
    # if not user_id:
    #     raise HTTPException(401, "Unauthorized")
    asset = await asset_crud.get(db, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")

    if asset.status != "available":
        raise HTTPException(400, "Asset not available")

    # asset_type = await type_crud.get(db, asset.asset_type_id)
    # if not asset_type.is_serialized:
    #     raise HTTPException(400, "Bulk asset cannot be individually assigned")

    staff = await staff_crud.get(db, data.staff_id)
    if not staff or not staff.is_active:
        raise HTTPException(400, "Invalid staff")

    if data.expected_return_date and \
       data.expected_return_date < data.assigned_date:
        raise HTTPException(400, "Invalid return date")

    active = await assignment_crud.get_by_fields(
        db,
        fields={"asset_id": asset_id, "is_active": True}
    )
    # if active:
        
    #     raise HTTPException(400, f"Asset already assigned  { [act.staff_id for act in active]}")

    await assignment_crud.create(
        db,
        obj_in={
            **data.model_dump(),
            "asset_id": asset_id,
            "is_active": True,
            "created_by": str(user_id),
            "updated_by": str(user_id)
        }
    )

    asset.status = "assigned"

    await db.commit()
    await db.refresh(asset)
    return SuccessResponse(message="Asset assigned successfully")



@router.post("/{asset_id}/return", response_model=SuccessResponse)
@require_permissions(["asset:create"])
async def return_asset(
    request: Request,
    asset_id: UUID,
    data: AssetReturnRequest,
    db: AsyncSession = Depends(get_db_session)
):
    assignment = await assignment_crud.get_by_fields(
        db,
        fields={"asset_id": asset_id, "is_active": True}
    )

    if not assignment:
        raise HTTPException(400, "No active assignment found")

    assignment = assignment[0]

    if data.returned_date < assignment.assigned_date:
        raise HTTPException(400, "Invalid return date")

    assignment.returned_date = data.returned_date
    assignment.condition_on_return = data.condition_on_return
    assignment.is_active = False

    asset = await asset_crud.get(db, asset_id)
    asset.status = "available"

    await db.commit()
    await db.refresh(assignment)

    return SuccessResponse(message="Asset returned successfully")


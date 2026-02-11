"""
Inventory management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.api.schemas import (
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse
)
from app.models.tenant import InventoryItem, InventoryCategory, InventoryLocation, InventoryStock, InventoryTransaction
from app.db.base import get_db_session
from app.services.crud import CRUDService
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory Management"])

item_crud = CRUDService(InventoryItem)
category_crud = CRUDService(InventoryCategory)
location_crud = CRUDService(InventoryLocation)
stock_crud = CRUDService(InventoryStock)
transaction_crud = CRUDService(InventoryTransaction)


@router.get("/items", response_model=PaginatedResponse)
async def list_inventory_items(
    request: Request,
    pagination: PaginationParams = Depends(),
    category_id: Optional[UUID] = None,
    location_id: Optional[UUID] = None,
    low_stock: Optional[bool] = False,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List inventory items with filtering."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    filters = {"is_active": True}
    if category_id:
        filters["category_id"] = category_id
    
    total = await item_crud.count(db, tenant_id=tenant_id, filters=filters)
    
    items = await item_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        tenant_id=tenant_id,
        filters=filters
    )
    
    item_responses = []
    for item in items:
        # TODO: Get actual stock quantity
        stock_quantity = 0
        
        item_responses.append(InventoryItemResponse(
            id=item.id,
            sku=item.sku,
            name=item.name,
            description=item.description,
            category_id=item.category_id,
            unit_of_measure=item.unit_of_measure,
            barcode=item.barcode,
            manufacturer=item.manufacturer,
            model_number=item.model_number,
            cost_price=item.cost_price,
            selling_price=item.selling_price,
            reorder_level=item.reorder_level,
            reorder_quantity=item.reorder_quantity,
            is_trackable=item.is_trackable,
            is_consumable=item.is_consumable,
            is_active=item.is_active,
            deleted_at=item.deleted_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
            category_name=None,  # TODO: Fetch category name
            stock_quantity=stock_quantity
        ))
    
    return PaginatedResponse.create(
        items=item_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("/items", response_model=InventoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    request: Request,
    item_data: InventoryItemCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new inventory item."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    # Check if SKU already exists
    existing = await item_crud.get_by_field(
        db,
        field="sku",
        value=item_data.sku,
        tenant_id=tenant_id
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Item with this SKU already exists"
        )
    
    item = await item_crud.create(
        db,
        obj_in=item_data.model_dump(),
        tenant_id=tenant_id
    )
    
    logger.info(f"Inventory item created: {item.id}")
    
    return InventoryItemResponse(
        id=item.id,
        sku=item.sku,
        name=item.name,
        description=item.description,
        category_id=item.category_id,
        unit_of_measure=item.unit_of_measure,
        barcode=item.barcode,
        manufacturer=item.manufacturer,
        model_number=item.model_number,
        cost_price=item.cost_price,
        selling_price=item.selling_price,
        reorder_level=item.reorder_level,
        reorder_quantity=item.reorder_quantity,
        is_trackable=item.is_trackable,
        is_consumable=item.is_consumable,
        is_active=item.is_active,
        deleted_at=item.deleted_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        stock_quantity=0
    )


@router.get("/items/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    request: Request,
    item_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific inventory item by ID."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    item = await item_crud.get(db, item_id, tenant_id=tenant_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    return InventoryItemResponse(
        id=item.id,
        sku=item.sku,
        name=item.name,
        description=item.description,
        category_id=item.category_id,
        unit_of_measure=item.unit_of_measure,
        barcode=item.barcode,
        manufacturer=item.manufacturer,
        model_number=item.model_number,
        cost_price=item.cost_price,
        selling_price=item.selling_price,
        reorder_level=item.reorder_level,
        reorder_quantity=item.reorder_quantity,
        is_trackable=item.is_trackable,
        is_consumable=item.is_consumable,
        is_active=item.is_active,
        deleted_at=item.deleted_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        stock_quantity=0
    )


@router.put("/items/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(
    request: Request,
    item_id: UUID,
    item_data: InventoryItemUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update an inventory item."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    item = await item_crud.get(db, item_id, tenant_id=tenant_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    updated_item = await item_crud.update(
        db,
        db_obj=item,
        obj_in=item_data.model_dump(exclude_unset=True)
    )
    
    logger.info(f"Inventory item updated: {updated_item.id}")
    
    return InventoryItemResponse(
        id=updated_item.id,
        sku=updated_item.sku,
        name=updated_item.name,
        description=updated_item.description,
        category_id=updated_item.category_id,
        unit_of_measure=updated_item.unit_of_measure,
        barcode=updated_item.barcode,
        manufacturer=updated_item.manufacturer,
        model_number=updated_item.model_number,
        cost_price=updated_item.cost_price,
        selling_price=updated_item.selling_price,
        reorder_level=updated_item.reorder_level,
        reorder_quantity=updated_item.reorder_quantity,
        is_trackable=updated_item.is_trackable,
        is_consumable=updated_item.is_consumable,
        is_active=updated_item.is_active,
        deleted_at=updated_item.deleted_at,
        created_at=updated_item.created_at,
        updated_at=updated_item.updated_at,
        stock_quantity=0
    )


@router.delete("/items/{item_id}", response_model=SuccessResponse)
async def delete_inventory_item(
    request: Request,
    item_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete an inventory item."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    item = await item_crud.delete(
        db,
        id=item_id,
        tenant_id=tenant_id,
        soft=True
    )
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    logger.info(f"Inventory item deleted: {item_id}")
    
    return SuccessResponse(message="Inventory item deleted successfully")


# ============================================
# Stock Routes
# ============================================

@router.get("/stock", response_model=List[dict])
async def list_stock(
    request: Request,
    item_id: Optional[UUID] = None,
    location_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List stock levels."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    filters = {}
    if item_id:
        filters["item_id"] = item_id
    if location_id:
        filters["location_id"] = location_id
    
    stocks = await stock_crud.get_multi(
        db,
        tenant_id=tenant_id,
        filters=filters
    )
    
    return [
        {
            "id": str(stock.id),
            "item_id": str(stock.item_id),
            "location_id": str(stock.location_id),
            "quantity_on_hand": stock.quantity_on_hand,
            "quantity_reserved": stock.quantity_reserved,
            "quantity_available": stock.quantity_on_hand - stock.quantity_reserved,
            "average_cost": float(stock.average_cost) if stock.average_cost else None,
            "last_movement_at": stock.last_movement_at.isoformat() if stock.last_movement_at else None
        }
        for stock in stocks
    ]


@router.post("/stock/adjust", response_model=SuccessResponse)
async def adjust_stock(
    request: Request,
    item_id: UUID,
    location_id: UUID,
    quantity: int,
    reason: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Adjust stock quantity."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    # Get or create stock record
    stocks = await stock_crud.get_by_fields(
        db,
        fields={"item_id": item_id, "location_id": location_id},
        tenant_id=tenant_id
    )
    
    if stocks:
        stock = stocks[0]
        old_quantity = stock.quantity_on_hand
        stock.quantity_on_hand += quantity
    else:
        old_quantity = 0
        stock = await stock_crud.create(
            db,
            obj_in={
                "item_id": item_id,
                "location_id": location_id,
                "quantity_on_hand": quantity,
                "quantity_reserved": 0
            },
            tenant_id=tenant_id
        )
    
    stock.last_movement_at = datetime.utcnow()
    await db.flush()
    
    # Create transaction record
    await transaction_crud.create(
        db,
        obj_in={
            "transaction_number": f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "item_id": item_id,
            "location_id": location_id,
            "transaction_type": "adjustment",
            "quantity": quantity,
            "notes": reason,
            "performed_by": user_id
        },
        tenant_id=tenant_id
    )
    
    # Check for low stock
    item = await item_crud.get(db, item_id, tenant_id=tenant_id)
    if item and stock.quantity_on_hand <= item.reorder_level:
        await publish_event(
            event_type=EventType.INVENTORY_LOW_STOCK,
            aggregate_type="inventory",
            aggregate_id=str(item_id),
            tenant_id=tenant_id,
            payload={
                "item_name": item.name,
                "sku": item.sku,
                "quantity_on_hand": stock.quantity_on_hand,
                "reorder_level": item.reorder_level
            }
        )
    
    logger.info(f"Stock adjusted for item {item_id}: {old_quantity} -> {stock.quantity_on_hand}")
    
    return SuccessResponse(
        message=f"Stock adjusted successfully. New quantity: {stock.quantity_on_hand}"
    )


# ============================================
# Categories & Locations
# ============================================

@router.get("/categories", response_model=List[dict])
async def list_categories(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """List all inventory categories."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    categories = await category_crud.get_multi(
        db,
        tenant_id=tenant_id,
        filters={"is_active": True}
    )
    
    return [
        {
            "id": str(cat.id),
            "name": cat.name,
            "code": cat.code,
            "description": cat.description,
            "parent_id": str(cat.parent_id) if cat.parent_id else None
        }
        for cat in categories
    ]


@router.get("/locations", response_model=List[dict])
async def list_locations(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """List all inventory locations."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    locations = await location_crud.get_multi(
        db,
        tenant_id=tenant_id,
        filters={"is_active": True}
    )
    
    return [
        {
            "id": str(loc.id),
            "name": loc.name,
            "code": loc.code,
            "location_type": loc.location_type,
            "description": loc.description
        }
        for loc in locations
    ]

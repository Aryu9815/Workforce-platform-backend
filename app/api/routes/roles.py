from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from app.db.base import get_db_session
from app.schemas import RoleCreate, RoleUpdate
from app.utils.rbac_middleware import require_permissions
from app.core.logging_config import get_logger
from app.models.tenant import (
    Role,
    RolePermission
)
from app.services import notify
from app.services.crud import role_crud, role_permission_crud
from app.core.constants import ROLE_NOT_FOUND

logger = get_logger(__name__)
router = APIRouter(prefix="/roles", tags=["Role Management"])

# ============================================================
# LIST ROLES
# ============================================================

async def _check_role_exists(db, role_id):
    role = await role_crud.get(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ROLE_NOT_FOUND)
    return role

async def _check_existing_default_roles(db):
    default_role = await role_crud.get_by_fields(
        db,
        fields={"is_default": True, "is_deleted": False}
    )

    if default_role:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only one role set as default")


@router.get("", response_model=List[dict])
# @require_permissions(["role:view"])
async def list_roles(
    request: Request,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Role).where(Role.is_deleted == False)

    if search:
        stmt = stmt.where(Role.name.ilike(f"%{search}%"))

    result = await db.execute(stmt)
    roles = result.scalars().all()

    return [
        {
            "id": str(role.id),
            "name": role.name,
            "description": role.description,
            "is_active": role.is_active,
            "is_system": role.is_system,
            "is_default": role.is_default
        }
        for role in roles
    ]


# ============================================================
# GET ROLE DETAIL
# ============================================================
@router.get("/{role_id}", response_model=dict)
# @require_permissions(["role:view"])
async def get_role(
    request: Request,
    role_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    
    role = await _check_role_exists(db, role_id)

    # Get assigned permission IDs only
    stmt = select(RolePermission.permission_id).where(
        RolePermission.role_id == role_id,
        RolePermission.is_deleted == False,
        RolePermission.is_active == True
    )

    result = await db.execute(stmt)
    permission_ids = [str(row[0]) for row in result.all()]

    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "is_active": role.is_active,
        "is_default": role.is_default,
        "is_system": role.is_system,
        "permissions": permission_ids
    }



# ============================================================
# CREATE ROLE
# ============================================================

@router.post("", response_model=dict, status_code=201)
@require_permissions(["role:create"])
async def create_role(
    request: Request,
    data: RoleCreate,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    existing = await role_crud.get_by_fields(
        db,
        fields={"name": data.name, "is_deleted": False}
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    
    if data.is_default:
        await _check_existing_default_roles(db)

    role = await role_crud.create(
        db,
        obj_in=data.model_dump(),
        user_id=str(user_id)
    )

    await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': f"New role {role.name}",
            'message': f"You have added a new role named {role.name}",
            }
        )
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description
    }


# ============================================================
# UPDATE ROLE
# ============================================================

@router.put("/{role_id}", response_model=dict)
@require_permissions(["role:update"])
async def update_role(
    request: Request,
    role_id: UUID,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    role = await _check_role_exists(db, role_id)
    if data.is_default:
        await _check_existing_default_roles(db)

    # Update basic fields if provided
    update_data = data.model_dump(exclude_unset=True, exclude={"permissions"})

    for field, value in update_data.items():
        setattr(role, field, value)

    role.updated_by = str(user_id)

    # Only sync permissions if sent
    if data.permissions:
        new_permissions = set(UUID(p) for p in data.permissions)

        stmt = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.is_deleted == False
        )

        result = await db.execute(stmt)
        existing_mappings = result.scalars().all()

        existing_permission_ids = {rp.permission_id for rp in existing_mappings}

        # Remove unselected
        for rp in existing_mappings:
            if rp.permission_id not in new_permissions:
                rp.is_deleted = True
                rp.updated_by = str(user_id)

        # Add new ones
        for perm_id in new_permissions - existing_permission_ids:
            await role_permission_crud.create(
                db,
                obj_in={
                    "role_id": role_id,
                    "permission_id": perm_id,
                    "created_by": str(user_id),
                    "updated_by": str(user_id)
                }
            )

    await db.commit()
    await db.refresh(role)
    await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': f"Updated role {role.name}",
            'message': f"You have updated a role named {role.name}",
            }
        )
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "is_default": role.is_default,
        "is_active": role.is_active
    }


# ============================================================
# DELETE ROLE (SOFT DELETE)
# ============================================================

@router.delete("/{role_id}", status_code=204)
@require_permissions(["role:delete"])
async def delete_role(
    request: Request,
    role_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    role = await role_crud.get(db, role_id)

    if not role or role.is_deleted:
        raise HTTPException(404, ROLE_NOT_FOUND)

    role.is_deleted = True
    role.updated_by = str(user_id)

    await db.commit()
    await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': f"Deleted role {role.name}",   
            'message': f"You have deleted a role named {role.name}",
            }
        )
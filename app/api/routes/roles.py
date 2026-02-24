"""
Role management API routes.
ERP-grade RBAC module.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.db.base import get_db_session
from app.services.crud import CRUDService
from app.utils.rbac_middleware import require_permissions
from app.core.logging_config import get_logger

from app.models.tenant.rbac_models import (
    Role,
    Permission,
    RolePermission
)

logger = get_logger(__name__)
router = APIRouter(prefix="/roles", tags=["Role Management"])

role_crud = CRUDService(Role)
permission_crud = CRUDService(Permission)
role_permission_crud = CRUDService(RolePermission)


# ============================================================
# LIST ROLES
# ============================================================

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
async def get_role(
    request: Request,
    role_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    role = await role_crud.get(db, role_id)

    if not role or role.is_deleted:
        raise HTTPException(404, "Role not found")

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
# @require_permissions(["role:create"])
async def create_role(
    request: Request,
    data: dict,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "Unauthorized")

    existing = await role_crud.get_by_fields(
        db,
        fields={"name": data["name"], "is_deleted": False}
    )

    if existing:
        raise HTTPException(409, "Role name already exists")

    role = await role_crud.create(
        db,
        obj_in={
            "name": data["name"],
            "description": data.get("description"),
            "created_by": str(user_id),
            "updated_by": str(user_id)
        }
    )

    # Attach permissions if provided
    permissions = data.get("permission_ids", [])

    for perm_id in permissions:
        perm = await permission_crud.get(db, perm_id)
        if not perm:
            raise HTTPException(404, f"Permission {perm_id} not found")

        await role_permission_crud.create(
            db,
            obj_in={
                "role_id": role.id,
                "permission_id": perm_id,
                "created_by": str(user_id),
                "updated_by": str(user_id)
            }
        )

    await db.commit()
    await db.refresh(role)

    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description
    }


# ============================================================
# UPDATE ROLE
# ============================================================

@router.put("/{role_id}", response_model=dict)
async def update_role(
    request: Request,
    role_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "common_id", None)
    if not user_id:
        raise HTTPException(401, "Unauthorized")

    role = await role_crud.get(db, role_id)

    if not role or role.is_deleted:
        raise HTTPException(404, "Role not found")

    # Update basic fields if provided
    if "name" in data:
        role.name = data["name"]

    if "description" in data:
        role.description = data["description"]

    if "is_default" in data:
        role.is_default = data["is_default"]

    role.updated_by = str(user_id)

    # Only sync permissions if sent
    if "permissions" in data:
        new_permissions = set(UUID(p) for p in data["permissions"])

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
# @require_permissions(["role:delete"])
async def delete_role(
    request: Request,
    role_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, "common_id", None)

    role = await role_crud.get(db, role_id)

    if not role or role.is_deleted:
        raise HTTPException(404, "Role not found")

    role.is_deleted = True
    role.updated_by = str(user_id)

    await db.commit()

    return
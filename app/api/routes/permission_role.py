from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from app.db.base import get_db_session
from app.core.logging_config import get_logger
from app.utils.rbac_middleware import require_permissions
from app.models.tenant import (
    RolePermission,
    Role,
    Permission
)
from app.schemas import SuccessResponse
from app.services.notification import notify
from app.services.crud import role_permission_crud 

logger = get_logger(__name__)
router = APIRouter(
    prefix="/role-permissions",
    tags=["Role Permission Management"]
)


# ============================================================
# List Role Permissions (Admin Panel Grid)
# ============================================================

@router.get("", response_model=List[dict])
@require_permissions(["role:view"])
async def list_role_permissions(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns role-permission mapping list
    including role name and permission code.
    """

    stmt = (
        select(
            RolePermission,
            Role.name.label("role_name"),
            Permission.code.label("permission_code"),
            Permission.name.label("permission_name")
        )
        .join(Role, Role.id == RolePermission.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.is_deleted == False)
    )

    result = await db.execute(stmt)
    records = result.all()

    response = []

    for rp, role_name, permission_code, permission_name in records:
        response.append({
            "id": str(rp.id),
            "role_id": str(rp.role_id),
            "role_name": role_name,
            "permission_id": str(rp.permission_id),
            "permission_code": permission_code,
            "permission_name": permission_name,
            "is_active": rp.is_active,
            "conditions": rp.conditions,
            "created_at": rp.created_at
        })

    return response


# ============================================================
# Toggle Role Permission Active Status
# ============================================================

@router.patch("/{role_permission_id}/toggle", response_model=SuccessResponse)
@require_permissions(["role:update"])
async def toggle_role_permission(
    request: Request,
    role_permission_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Toggle is_active field for RolePermission.
    Used by admin panel switch.
    """

    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)
    role_permission = await role_permission_crud.get(db, role_permission_id , include_inactive=True)

    if not role_permission or role_permission.is_deleted:
        raise HTTPException(status_code=404, detail="Role permission not found")

    # Toggle status
    role_permission.is_active = not role_permission.is_active
    role_permission.updated_by = str(user_id)

    await db.commit()
    await db.refresh(role_permission)
    await notify.notify_role_permissions(db, role_permission, tenant_id, user_id)
    return SuccessResponse(
        message="Role permission status updated successfully"
    )
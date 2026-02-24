"""
Permission listing API.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.base import get_db_session
from app.models.tenant.rbac_models import Permission
from app.utils.rbac_middleware import require_permissions

router = APIRouter(prefix="/permissions", tags=["Permission Management"])


@router.get("", response_model=List[dict])
# @require_permissions(["role:view"])
async def list_permissions(
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Permission).where(Permission.is_deleted == False)

    result = await db.execute(stmt)
    permissions = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "resource": p.resource,
            "action": p.action,
            "is_active": p.is_active
        }
        for p in permissions
    ]
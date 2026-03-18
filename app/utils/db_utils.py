from app.services.crud import staff_crud
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.utils.cache_utils import cache_utils
from app.schemas import StaffResponse


async def get_staff(db: AsyncSession, staff_id: UUID, tenant_id: UUID):
    staff = await cache_utils.get_or_set_staff(db, staff_id, tenant_id)
    if staff:
        return StaffResponse.model_validate(staff)
    staff = await staff_crud.get(db, staff_id)
    return staff
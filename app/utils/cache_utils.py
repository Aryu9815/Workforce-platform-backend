from uuid import UUID
from app.core.redis_manager import redis_manager
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.crud import staff_crud
import json
from app.utils.decorators import redis_required
from app.schemas import StaffResponse
class CacheUtils:

    @property
    def redis_client(self):
        return redis_manager.redis_client
    
    @redis_required
    async def get_staff(self, staff_id: UUID, tenant_id: UUID):
        cache_key = f"staff:{tenant_id}:{staff_id}"
        cached_staff = await self.redis_client.get(cache_key)
        return cached_staff
    
    @redis_required
    async def get_all_staff_base_data(self, tenant_id: UUID):
        tenant_set = f"tenant_staff_base:{tenant_id}"
        cached_staff = await self.redis_client.smembers(tenant_set)
        return [json.loads(s) for s in cached_staff]
    
    @redis_required
    async def set_staff(self, staff_id: UUID, tenant_id: UUID, staff_data):
        cache_key = f"staff:{tenant_id}:{staff_id}"
        await self.redis_client.set(cache_key, staff_data)

    @redis_required
    async def set_all_staff_base_data(self, tenant_id: UUID, staff_data):
        tenant_set = f"tenant_staff_base:{tenant_id}"
        await self.redis_client.sadd(
            tenant_set,
            *[json.dumps(staff) for staff in staff_data]
        )
    
    @redis_required
    async def get_or_set_all_staff_base_data(self, db: AsyncSession, tenant_id: UUID):
        cached_staff = await self.get_all_staff_base_data(tenant_id)
        if cached_staff:
            return cached_staff
        staff_list = await staff_crud.get_multi(db, filters={"is_active": True})
        staff_data = [
            {
                "staff_id": str(staff.id),
                "user_id": str(staff.user_id),
                "name": f"{staff.first_name} {staff.last_name}",
                "first_name": staff.first_name,
                "last_name": staff.last_name,
                "email": staff.email
            }
            for staff in staff_list
        ]
        await self.set_all_staff_base_data(tenant_id, staff_data)
        return staff_data
    
    @redis_required
    async def get_or_set_staff(self, db: AsyncSession, staff_id: UUID, tenant_id: UUID):
        cached_staff = await self.get_staff(staff_id, tenant_id)
        if cached_staff:
            return json.loads(cached_staff)
        staff = await staff_crud.get(db, staff_id)
        if not staff:
            return None
        staff_data = StaffResponse.model_validate(staff)
        await self.set_staff(staff_id, tenant_id, staff_data.model_dump_json())
        return staff_data.model_dump()

    @redis_required
    async def set_user_notifications_cache(self, user_id: str, tenant_id: str, notification_data):

        key = f"notifications:{tenant_id}:{user_id}"
        print('set notifications', key)
        await self.redis_client.lpush(key,json.dumps(notification_data, default=str))
        # keep only last 50 notifications
        await self.redis_client.ltrim(key, 0, 49)

    @redis_required
    async def get_user_notifications_cache(self, user_id: str, tenant_id: str):
        key = f"notifications:{tenant_id}:{user_id}"
        print('get notifications', key)
        notifications = await self.redis_client.lrange(key, 0, 19)

        if notifications:
            return [json.loads(n) for n in notifications]

        return notifications


cache_utils = CacheUtils()
        
    

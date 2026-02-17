from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

from app.db.db_connection import get_common_session_maker
from app.db.tenant_connection import get_tenant_session
from app.db.base import set_tenant_context, clear_tenant_context
from app.services.leave import LeaveService
from app.models.common.tenant_master import TenantMaster   # ← your tenant table model



scheduler = AsyncIOScheduler()
leave_service = LeaveService()


async def monthly_accrual_job():
    """
    Runs on 1st of every month.
    Executes accrual for ALL active tenants.
    """

    today = datetime.now().date()

    # previous month
    if today.month == 1:
        year = today.year - 1
        month = 12
    else:
        year = today.year
        month = today.month - 1

    common_session_maker = await get_common_session_maker()

    async with common_session_maker() as common_db:

        # 1️⃣ Fetch active tenants
        result = await common_db.execute(
            select(TenantMaster).where(TenantMaster.is_active == True)
        )

        tenants = result.scalars().all()

        for tenant in tenants:
            tenant_id = str(tenant.tenant_id)

            # 2️⃣ Set tenant context
            set_tenant_context(tenant_id)

            tenant_session_maker = await get_tenant_session(
                common_db,
                tenant_id
            )

            async with tenant_session_maker() as tenant_db:
                try:
                    await leave_service.accrue_monthly_leaves(
                        db=tenant_db,
                        year=year,
                        month=month
                    )
                except Exception as e:
                    # Log error per tenant
                    print(f"Accrual failed for tenant {tenant_id}: {e}")

            clear_tenant_context()
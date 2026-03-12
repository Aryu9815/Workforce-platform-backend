from app.models.common import NotificationJobs, PushSubscription
from app.db.base import get_common_session_maker, clear_tenant_context, set_tenant_context
from app.utils.email_sender import send_email
from app.utils.push_sender import send_push
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Notifications
from app.services.crud import tenant_master_crud
from app.db.tenant_connection import get_tenant_session
from app.services import notify

async def process_pending_jobs():
    print("Worker: Checking for pending notification jobs...")
    session_maker = await get_common_session_maker()

    # STEP 1 — Fetch jobs in short transaction
    async with session_maker() as session:
        result = await session.execute(
            NotificationJobs.__table__.select()
            .where(NotificationJobs.status == "pending")
        )
        jobs = result.fetchall()

    # Transaction closed here

    # STEP 2 — Process each job independently
    for job in jobs:

        try:
            if hasattr(job, "tenant_id"):
                set_tenant_context(job.tenant_id)

            # ---- Channel Handling ----
            if job.channel == "email":
                await send_email(job.payload)

            elif job.channel == "push":
                async with session_maker() as session:
                    sub_query = await session.execute(
                        PushSubscription.__table__.select().where(
                            PushSubscription.user_id == job.payload["user_id"]
                        )
                    )
                    subscription = sub_query.first()

                if subscription:
                    await send_push(subscription, {
                        "title": job.payload["title"],
                        "message": job.payload["message"],
                        "url": job.payload.get("url", "/")
                    })

            # STEP 3 — Mark success in new short transaction
            async with session_maker() as session:
                async with session.begin():
                    await session.execute(
                        NotificationJobs.__table__.update()
                        .where(NotificationJobs.id == job.id)
                        .values(status="sent")
                    )

        except Exception as e:
            print("Worker Error:", e)

            # STEP 4 — Increment attempts safely
            async with session_maker() as session:
                async with session.begin():
                    await session.execute(
                        NotificationJobs.__table__.update()
                        .where(NotificationJobs.id == job.id)
                        .values(attempts=job.attempts + 1)
                    )

        finally:
            clear_tenant_context()


async def cleanup_old_notifications(session: AsyncSession, weeks: int = 4):
    cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    stmt = delete(Notifications).where(Notifications.created_at < cutoff_date)
    await session.execute(stmt)
    await session.commit()
    

async def notification_cleaner():
    session_maker = await get_common_session_maker()
    tenants = []
    async with session_maker() as session:
        tenants = await tenant_master_crud.get_by_fields(session, fields={'is_deleted': False})
        for tenant in tenants:
            tenant_session = await get_tenant_session(session, tenant.tenant_id)
            async with tenant_session() as tnt_session:
                try:
                    set_tenant_context(tenant.tenant_id)
                    await cleanup_old_notifications(tnt_session)
                    print(f"Cleaned notifications for tenant {tenant.tenant_id}")
                finally:
                    clear_tenant_context()

async def task_alert_job():
    session_maker = await get_common_session_maker()
    tenants = []
    async with session_maker() as session:
        tenants = await tenant_master_crud.get_by_fields(session, fields={'is_deleted': False})
        for tenant in tenants:
            tenant_session = await get_tenant_session(session, tenant.tenant_id)
            async with tenant_session() as tnt_session:
                await notify.notify_task_deadline_alert(tnt_session, tenant.tenant_id)
                
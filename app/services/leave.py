# app/services/attendance_service.py

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import AttendanceRecord, Shift, LeaveRequest, Holiday
from app.schemas.attendance import LeaveRequestCreate
from app.services.crud import CRUDService
from app.events.publisher import publish_event, EventType
from app.models.tenant.staff import StaffProfile

class LeaveService:

    def __init__(self):
        self.attendance_crud = CRUDService(AttendanceRecord)
        self.shift_crud = CRUDService(Shift)
        self.leave_crud = CRUDService(LeaveRequest)
        self.holiday_crud = CRUDService(Holiday)
        self.staff_crud = CRUDService(StaffProfile)


    async def approve_leave(
        self,
        db: AsyncSession,
        leave_id: UUID,
        approver_id: UUID,
        approval_status: str,
        notes: str | None = None,
    ):

        leave = await self.leave_crud.get(db, leave_id)

        if not leave:
            raise HTTPException(404, "Leave not found")

        if leave.status != "pending":
            raise HTTPException(409, "Already processed")

        if approval_status == "approved":

            # 1️⃣ Fetch leave balance
            balance = await self.leave_balance_crud.get_by_fields(
                db,
                fields={
                    "staff_id": leave.staff_id,
                    "leave_type_id": leave.leave_type_id,
                    "year": leave.start_date.year,
                },
            )

            if not balance:
                raise HTTPException(400, "Leave balance not initialized")

            balance = balance[0]

            # 2️⃣ Validate quota
            if balance.remaining_days < leave.days_requested:
                raise HTTPException(400, "Insufficient leave balance")

            # 3️⃣ Deduct balance
            balance.used_days += leave.days_requested
            balance.remaining_days -= leave.days_requested

            # 4️⃣ Create attendance entries
            current_date = leave.start_date
            while current_date <= leave.end_date:

                await self.attendance_crud.create(
                    db,
                    obj_in={
                        "staff_id": leave.staff_id,
                        "date": current_date,
                        "status": "leave",
                        "is_manual_entry": True,
                        "notes": "Approved Leave",
                        "created_by": approver_id,
                    },
                )

                current_date += timedelta(days=1)

        # 5️⃣ Update leave record
        leave.status = approval_status
        leave.approved_by = approver_id
        leave.approved_at = datetime.now(timezone.utc)
        leave.approval_notes = notes

        await db.commit()
        await db.refresh(leave)

        return leave
    async def create_leave(self , db: AsyncSession, leave_data: LeaveRequestCreate, current_user_id: UUID):
            
        leave = await self.leave_crud.create(
            db,
            obj_in={**leave_data.model_dump(), "created_by": current_user_id}
        )
        await db.commit()
        await db.refresh(leave)
        # Publish event
        await publish_event(
            event_type=EventType.LEAVE_REQUESTED,
            aggregate_type="leave",
            aggregate_id=str(leave.id),
            payload={
                "staff_id": str(leave.staff_id),
                "leave_type_id": str(leave.leave_type_id),
                "start_date": leave.start_date.isoformat(),
                "end_date": leave.end_date.isoformat(),
                "days": leave.days_requested
            }
        )
        return leave


# app/services/attendance_service.py
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Shift
from app.services.crud import (
    leave_crud,
    holiday_crud,
    attendance_crud,
    shift_crud ,
    staff_crud
)
from app.services.task_work_service import task_work_service

class AttendanceService:

    def __init__(self):
        pass


    # ==========================================================
    # CHECK IN
    # ==========================================================
    async def check_in(
        self,
        db: AsyncSession,
        staff_id: UUID,
        user_id: UUID,
        location: dict | None = None,
    ):

        now = datetime.now(timezone.utc)
        today = now.date()

        # 1️⃣ Check holiday
        holiday = await holiday_crud.get_by_fields(
            db, fields ={"date": today}
        )
        if holiday:
            raise HTTPException(400, "Today is a holiday")

        # 2️⃣ Check approved leave
        leave = await leave_crud.get_by_fields(
            db,
            fields=
            {
                "staff_id": staff_id,
                "start_date": today,
                "status": "approved",
            },
        )
        if leave:
            raise HTTPException(400, "Staff is on approved leave")

        # 3️⃣ Prevent duplicate check-in
        existing = await attendance_crud.get_by_fields(
            db,
           fields= {"staff_id": staff_id, "date": today},
        )
        if existing:
            raise HTTPException(409, "Already checked in today")

        # 4️⃣ Fetch shift
        shift = await self._get_staff_shift(db, staff_id)

        status = "present"

        if shift:
            grace_time = (
                datetime.combine(today, shift.start_time)
                + timedelta(minutes=10)
            ).time()

            if now.time() > grace_time:
                status = "late"

        record = await attendance_crud.create(
            db,
            obj_in={
                "staff_id": staff_id,
                "date": today,
                "shift_id": shift.id if shift else None,
                "check_in": now,
                "check_in_location": location,
                "check_in_method": "web",
                "status": status,
                "created_by": user_id,
            },
        )

        await db.commit()
        await db.refresh(record)

        return record

    # ==========================================================
    # CHECK OUT
    # ==========================================================
    async def check_out(
        self,
        db: AsyncSession,
        staff_id: UUID,
        user_id: UUID,
        location: dict | None = None,
        notes: str | None = None,
    ):

        now = datetime.now(timezone.utc)
        today = now.date()

        records = await attendance_crud.get_by_fields(
            db,
            fields = {"staff_id": staff_id, "date": today},
        )

        if not records:
            raise HTTPException(404, "No check-in record found")

        record = records[0]

        if not record.check_in:
            raise HTTPException(400, "Invalid attendance state")

        if record.check_out:
            raise HTTPException(409, "Already checked out")

        shift = await self._get_staff_shift(db, staff_id)

        await task_work_service.end_day(
            db=db,
            staff_id=staff_id,
            user_id=user_id,
        )
        # Update checkout
        record.check_out = now
        record.check_out_location = location
        record.check_out_method = "web"
        record.updated_by = user_id

        if notes:
            record.notes = notes

        # Calculate work hours
        # duration = now - record.check_in
        # work_hours = round(duration.total_seconds() / 3600, 2)
        work_hours = float(record.work_hours or 0)
        # record.work_hours = Decimal(str(work_hours))
        # --------------------------------------------------
        # 1️⃣ Close all open task sessions first
        # --------------------------------------------------

        # Half Day
        if work_hours < 4:
            record.status = "half_day"

        # Overtime
        if shift:
            shift_hours = self._calculate_shift_hours(shift)

            if work_hours > shift_hours:
                record.overtime_hours = Decimal(
                    str(work_hours - shift_hours)
                )

            # Early Exit
            shift_end_time = shift.end_time
            if now.time() < shift_end_time:
                record.status = "early_exit"

        await db.commit()
        await db.refresh(record)
        return record

    # ==========================================================
    # PRIVATE HELPERS
    # ==========================================================

    async def _get_staff_shift(
        self,
        db: AsyncSession,
        staff_id: UUID,
    ) -> Shift | None:
        """
        Fetch active shift assigned to staff.
        Validates:
        - shift exists
        - shift is active
        - today is working day
        """

        # 1️⃣ Fetch staff
        staff = await staff_crud.get(db, staff_id)

        if not staff:
            raise HTTPException(404, "Staff not found")

        if not getattr(staff, "shift_id", None):
            return None

        # 2️⃣ Fetch shift (CRUD already filters is_active & is_deleted)
        shift = await shift_crud.get(
            db,
            staff.shift_id,
            include_deleted=False,
            include_inactive=False,
        )

        if not shift:
            return None
        

        now = datetime.now(timezone.utc)

        if shift.is_night_shift:
            # If before 5 AM, treat as previous working day
            if now.hour < 5:
                weekday = (now.weekday() - 1) % 7
            else:
                weekday = now.weekday()
        else:
            weekday = now.weekday()

        if shift.days_of_week and weekday not in shift.days_of_week:
            return None  # Not scheduled today
        # Monday = 0 ... Sunday = 6

        

        return shift

    def _calculate_shift_hours(self, shift: Shift) -> float:
        """
        Calculate total shift hours excluding break.
        """

        start = datetime.combine(datetime.today(), shift.start_time)
        end = datetime.combine(datetime.today(), shift.end_time)

        if shift.is_night_shift and end < start:
            end += timedelta(days=1)

        total_hours = (end - start).total_seconds() / 3600
        total_hours -= shift.break_duration_minutes / 60

        return round(total_hours, 2)

attendance_service = AttendanceService()
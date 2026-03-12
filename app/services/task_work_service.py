from zoneinfo import ZoneInfo
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional, List
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.tenant import (
    TaskWorkSession,
    AttendanceRecord,
    Task,
)
from app.services.crud import task_work_session_crud as session_crud, task_crud
from app.core.constants import ASIA_KOLKATA, TASK_NOT_FOUND

class TaskWorkService:

    def __init__(self):
        """Future implementation"""
        pass

    # ==========================================================
    # PUBLIC API
    # ==========================================================

    async def switch_task(
        self,
        db: AsyncSession,
        staff_id: UUID,
        task_id: UUID,
        user_id: UUID,
    ) -> TaskWorkSession:
        """
        Switch task:
        - Auto close previous open session
        - Create new session
        """

        IST = ZoneInfo(ASIA_KOLKATA)
        now = datetime.now(IST)
        today = now.date()

        attendance = await self._get_active_attendance(
            db, staff_id, today
        )

        last_session = await self._get_open_session_for_update(
            db, attendance.id
        )

        next_sequence = 1

        if last_session:
            if last_session.task_id == task_id:
                return last_session

            await self._close_session(
                db,
                last_session,
                now,
                user_id,
            )

            next_sequence = last_session.sequence + 1

        # Validate task exists
        task = await task_crud.get(db, task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)

        new_session = await session_crud.create(
            db,
            obj_in={
                "attendance_id": attendance.id,
                "task_id": task_id,
                "staff_id": staff_id,
                "check_in": now,
                "sequence": next_sequence,
                "created_by": user_id,
            },
        )

        return new_session

    async def end_day(
        self,
        db: AsyncSession,
        staff_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Called before attendance check_out.
        Ensures last session is closed.
        """

        IST = ZoneInfo(ASIA_KOLKATA)
        now = datetime.now(IST)
        today = now.date()

        attendance = await self._get_active_attendance(
            db, staff_id, today
        )

        open_session = await self._get_open_session_for_update(
            db, attendance.id
        )

        if open_session:
            await self._close_session(
                db,
                open_session,
                now,
                user_id,
            )


    async def get_sessions_by_attendance(
        self,
        db: AsyncSession,
        attendance_id: UUID,
    ) -> List[TaskWorkSession]:

        result = await db.execute(
            select(TaskWorkSession, Task)
            .join(Task, Task.id == TaskWorkSession.task_id)
            .where(
                TaskWorkSession.attendance_id == attendance_id,
                TaskWorkSession.is_deleted.is_(False),
            )
            .order_by(TaskWorkSession.sequence.asc())
        )

        rows = result.all()
        sessions = []
        for session, task in rows:
            session.task_name = (
                f"{task.ticket_code} - {task.ticket_number}"
                if task else None
            )
            sessions.append(session)
            

        return sessions

    # ==========================================================
    # PRIVATE METHODS
    # ==========================================================

    async def _get_active_attendance(
        self,
        db: AsyncSession,
        staff_id: UUID,
        today,
    ) -> AttendanceRecord:

        result = await db.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.staff_id == staff_id,
                AttendanceRecord.date == today,
                AttendanceRecord.is_deleted.is_(False),
            )
            .with_for_update()
        )

        attendance = result.scalar_one_or_none()

        if not attendance:
            raise HTTPException(
                400,
                "Attendance not found. Please check-in first."
            )

        if attendance.check_out:
            raise HTTPException(
                400,
                "Cannot switch task after checkout."
            )

        return attendance

    async def _get_open_session_for_update(
        self,
        db: AsyncSession,
        attendance_id: UUID,
    ) -> Optional[TaskWorkSession]:

        result = await db.execute(
            select(TaskWorkSession)
            .where(
                TaskWorkSession.attendance_id == attendance_id,
                TaskWorkSession.check_out.is_(None),
                TaskWorkSession.is_deleted.is_(False),
            )
            .order_by(TaskWorkSession.sequence.desc())
            .limit(1)
            .with_for_update()
        )

        return result.scalar_one_or_none()

    async def _close_session(
        self,
        db: AsyncSession,
        session: TaskWorkSession,
        close_time: datetime,
        user_id: UUID,
    ) -> None:

        duration_seconds = (close_time - session.check_in).total_seconds()
        hours = Decimal(str(round(duration_seconds / 3600, 2)))

        session.check_out = close_time
        session.duration_hours = hours
        session.updated_by = user_id

        await db.flush()

        await self._update_task_actual_hours(
            db,
            session.task_id,
            hours,
        )

    async def _update_task_actual_hours(
        self,
        db: AsyncSession,
        task_id: UUID,
        hours: Decimal,
    ) -> None:

        await db.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(
                actual_hours=func.coalesce(Task.actual_hours, 0) + hours
            )
        )

    async def get_today_sessions(
        self,
        db: AsyncSession,
        staff_id: UUID,
    ) -> List[TaskWorkSession]:

        IST = ZoneInfo(ASIA_KOLKATA)
        today = datetime.now(IST).date()

        result = await db.execute(
            select(AttendanceRecord.id)
            .where(
                AttendanceRecord.staff_id == staff_id,
                AttendanceRecord.date == today,
                AttendanceRecord.is_deleted.is_(False),
            )
        )

        attendance_id = result.scalar_one_or_none()

        if not attendance_id:
            return []

        sessions_result = await db.execute(
            select(TaskWorkSession)
            .where(
                TaskWorkSession.attendance_id == attendance_id,
                TaskWorkSession.is_deleted.is_(False),
            )
            .order_by(TaskWorkSession.sequence.asc())
        )

        return sessions_result.scalars().all()

task_work_service = TaskWorkService()
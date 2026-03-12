from datetime import date, datetime, timezone
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from app.models.tenant import StaffLeaveBalance, StaffProfile , LeaveType


class LeaveInitializationService:
    """
    Handles deterministic leave balance initialization.

    Responsibilities:
    - Initialize balances when staff is created
    - Backfill balances when new leave type is created
    - Idempotent (safe to call multiple times)
    """

    async def initialize_staff_leave_balances(
        self,
        db: AsyncSession,
        staff_id: UUID,
        join_date: date,
        created_by: str,
    ) -> None:
        """
        Initialize leave balance rows for a new staff member
        for the current year (join year).

        Does NOT allocate quota.
        Allocation handled strictly by accrual engine.
        """

        current_year = datetime.now(timezone.utc).year
        year = max(join_date.year, current_year)

        # Fetch active paid leave types
        result = await db.execute(
            select(LeaveType).where(
                LeaveType.is_active == True,
                LeaveType.is_paid == True,
                LeaveType.is_deleted == False,
            )
        )
        leave_types: List[LeaveType] = result.scalars().all()

        if not leave_types:
            return

        for lt in leave_types:
            # Check if balance already exists (idempotency)
            existing = await db.execute(
                select(StaffLeaveBalance).where(
                    StaffLeaveBalance.staff_id == staff_id,
                    StaffLeaveBalance.leave_type_id == lt.id,
                    StaffLeaveBalance.year == year,
                    StaffLeaveBalance.is_deleted == False,
                )
            )

            if existing.scalar_one_or_none():
                continue

            db.add(
                StaffLeaveBalance(
                    staff_id=staff_id,
                    leave_type_id=lt.id,
                    year=year,
                    allocated_days=Decimal("0.00"),
                    used_days=Decimal("0.00"),
                    remaining_days=Decimal("0.00"),
                    created_by=created_by,
                    updated_by=created_by,
                )
            )

    async def initialize_leave_type_for_existing_staff(
        self,
        db: AsyncSession,
        leave_type_id: UUID,
        year: int,
        created_by: str,
    ) -> None:
        """
        Backfill leave balance rows when a new leave type is created.
        Creates zero-balance entries for all active staff.
        """

        # Fetch leave type
        result = await db.execute(
            select(LeaveType).where(
                LeaveType.id == leave_type_id,
                LeaveType.is_deleted == False,
            )
        )
        leave_type = result.scalar_one_or_none()

        if not leave_type:
            return

        # Only paid leave types require balance tracking
        if not leave_type.is_paid:
            return

        # Fetch active staff
        result = await db.execute(
            select(StaffProfile).where(
                StaffProfile.is_active == True,
                StaffProfile.is_deleted == False,
            )
        )
        staff_members: List[StaffProfile] = result.scalars().all()

        for staff in staff_members:

            # Skip staff who joined after this year
            if staff.join_date.year > year:
                continue

            existing = await db.execute(
                select(StaffLeaveBalance).where(
                    StaffLeaveBalance.staff_id == staff.id,
                    StaffLeaveBalance.leave_type_id == leave_type_id,
                    StaffLeaveBalance.year == year,
                    StaffLeaveBalance.is_deleted == False,
                )
            )

            if existing.scalar_one_or_none():
                continue

            db.add(
                StaffLeaveBalance(
                    staff_id=staff.id,
                    leave_type_id=leave_type_id,
                    year=year,
                    allocated_days=Decimal("0.00"),
                    used_days=Decimal("0.00"),
                    remaining_days=Decimal("0.00"),
                    created_by=created_by,
                    updated_by=created_by,
                )
            )

leave_initialization_service = LeaveInitializationService()
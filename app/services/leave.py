# app/services/attendance_service.py

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import LeaveRequestCreate
from app.services.crud import(
    attendance_crud,shift_crud,leave_crud,
    staff_leave_balance_crud as leave_balance_crud,
    holiday_crud,leave_type_crud, leave_accrual_log_crud as accrual_log_crud,
    staff_crud
)
from app.utils.db_utils import get_staff

class LeaveService:

    def __init__(self):
        """Future implementation"""
        pass
    async def _check_leave_exists_or_pending(self, db, leave_id):
        leave = await leave_crud.get(db, leave_id)
        if not leave:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave not found")

        if leave.status != "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already processed")
        return leave

    async def _adjust_leave_balance(self, db, leave):

        balance = await leave_balance_crud.get_by_fields(
            db,
            fields={
                "staff_id": leave.staff_id,
                "leave_type_id": leave.leave_type_id,
                "year": leave.start_date.year,
            },
        )
        if not balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Leave balance not initialized. Accrual not processed for this period."
            )
        balance = balance[0]

        # Deduct balance
        leave_type = await leave_type_crud.get(db, leave.leave_type_id)
        if leave_type.is_paid:
            # Validate quota only for paid leave
            if balance.remaining_days < leave.days_requested:
                raise HTTPException(400, "Insufficient leave balance")
            balance.used_days += leave.days_requested
            balance.remaining_days -= leave.days_requested
            leave.is_payroll_deducted = False
        else:
            # unpaid leave
            leave.approval_notes = "Unpaid Leave - Payroll Deduction Applicable"
            leave.is_payroll_deducted = True

    async def _adjust_attendance(self, db, leave, approver_id, tenant_id):
        shift = await shift_crud.get(
            db,
            (await get_staff(db, leave.staff_id, tenant_id)).shift_id
        )
        current_date = leave.start_date
        while current_date <= leave.end_date:
            # Skip Holiday
            holiday = await holiday_crud.get_by_fields(
                db,
                fields={"date": current_date}
            )
            if holiday:
                current_date += timedelta(days=1)
                continue
            # Skip Non-working day based on shift
            if shift and shift.days_of_week:
                weekday = current_date.weekday()  # 0=Mon ... 6=Sun
                if weekday not in shift.days_of_week:
                    current_date += timedelta(days=1)
                    continue
            # Prevent duplicate attendance

            existing = await attendance_crud.get_by_fields(
                    db,
                    fields={
                        "staff_id": leave.staff_id,
                        "date": current_date,
                    },
                )
            if existing:
                record = existing[0]
                record.status = "leave"
                record.is_manual_entry = True
                record.notes = "Approved Leave"
                record.updated_by = approver_id
            else : 
                await attendance_crud.create(
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

    async def approve_leave(
        self,
        db: AsyncSession,
        leave_id: UUID,
        approver_id: UUID,
        approval_status: str,
        tenant_id: UUID,
        notes: str | None = None,
    ):

        leave = await self._check_leave_exists_or_pending(db, leave_id)

        if approval_status == "approved":

            await self._adjust_leave_balance(db, leave)

            # Create attendance entries
            await self._adjust_attendance(db, leave, approver_id, tenant_id)

        # 5️⃣ Update leave record
        leave.status = approval_status
        leave.approved_by = approver_id
        leave.approved_at = datetime.now(timezone.utc)
        leave.approval_notes = notes

        await db.commit()
        await db.refresh(leave)

        return leave
    
    async def create_leave(self , db: AsyncSession, leave_data: LeaveRequestCreate, current_user_id: UUID):
            
        leave = await leave_crud.create(
            db,
            obj_in={**leave_data.model_dump(), "created_by": current_user_id}
        )
        await db.commit()
        await db.refresh(leave)
        return leave

    async def _validate_accure_request(self, db, month, year):
        # Validate month range
        if month < 1 or month > 12:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month value")

        # Prevent future accrual
        today = datetime.now().date()

        if year > today.year or (year == today.year and month > today.month):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot accrue future period")

        # Check duplicate accrual
        existing = await accrual_log_crud.get_by_fields(
            db,
            fields={
                "year": year,
                "month": month,
            }
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Accrual already processed for {year}-{month}"
            )
        

    async def accrue_monthly_leaves(
        self,
        db: AsyncSession,
        year: int,
        month: int,
    ):
        """
        Strict ERP Monthly Accrual Engine

        - Prevents duplicate runs
        - Prevents future accrual
        - Respects join date
        - Accrues only paid leave
        - Fully transactional
        """

        await self._validate_accure_request(db, month, year)

        try:

            # Fetch active leave types (paid only)
            leave_types = await leave_type_crud.get_multi(
                db,
                filters={
                    "is_active": True,
                    "is_paid": True
                }
            )

            # Fetch active staff
            staff_members = await staff_crud.get_multi(
                db,
                filters={"is_active": True},
                limit=100000
            )

            for staff in staff_members:

                # Skip exited staff
                if (
                    staff.exit_date
                    or staff.join_date.year > year
                    or (staff.join_date.year == year and staff.join_date.month > month)
                ):
                    continue
                
                for lt in leave_types:

                    if not lt.max_days_per_year:
                        continue

                    # 5️⃣ Calculate monthly accrual
                    monthly_accrual = (
                        Decimal(str(lt.max_days_per_year)) / Decimal("12")
                    ).quantize(Decimal("0.01"))

                    balances = await leave_balance_crud.get_by_fields(
                        db,
                        fields={
                            "staff_id": staff.id,
                            "leave_type_id": lt.id,
                            "year": year,
                        },
                    )

                    if balances:
                        balance = balances[0]
                        balance.allocated_days += monthly_accrual
                        balance.remaining_days += monthly_accrual
                    else:
                        await leave_balance_crud.create(
                            db,
                            obj_in={
                                "staff_id": staff.id,
                                "leave_type_id": lt.id,
                                "year": year,
                                "allocated_days": monthly_accrual,
                                "used_days": Decimal("0"),
                                "remaining_days": monthly_accrual,
                                "created_by": "system"
                            }
                        )

            # 6️⃣ Log accrual execution (financial control)
            await accrual_log_crud.create(
                db,
                obj_in={
                    "year": year,
                    "month": month,
                    "status": "completed",
                    "created_by": "system"
                }
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

    async def carry_forward_leaves(self, db: AsyncSession, year: int):

        balances = await leave_balance_crud.get_multi(
            db,
            limit=100000,
            filters={"year": year}
        )

        for balance in balances:

            leave_type = await leave_type_crud.get(db, balance.leave_type_id)

            if not leave_type.carry_forward:
                continue

            carry_days = balance.remaining_days
            existing = await leave_balance_crud.get_by_fields(
                db,
                fields={
                    "staff_id": balance.staff_id,
                    "leave_type_id": balance.leave_type_id,
                    "year": year + 1,
                },
            )
            if existing:
                    
                await leave_balance_crud.create(
                    db,
                    obj_in={
                        "staff_id": balance.staff_id,
                        "leave_type_id": balance.leave_type_id,
                        "year": year + 1,
                        "allocated_days": carry_days,
                        "used_days": 0,
                        "remaining_days": carry_days,
                        "created_by": "system"
                    }
                )

        await db.commit()

leave_service = LeaveService()
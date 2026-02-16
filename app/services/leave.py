# app/services/attendance_service.py

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import AttendanceRecord, Shift, LeaveRequest, Holiday , LeaveType , LeaveAccrualLog
from app.schemas.attendance import LeaveRequestCreate
from app.services.crud import CRUDService
from app.events.publisher import publish_event, EventType
from app.models.tenant.staff import StaffProfile , StaffLeaveBalance

class LeaveService:

    def __init__(self):
        self.attendance_crud = CRUDService(AttendanceRecord)
        self.shift_crud = CRUDService(Shift)
        self.leave_crud = CRUDService(LeaveRequest)
        self.holiday_crud = CRUDService(Holiday)
        self.staff_crud = CRUDService(StaffProfile)
        self.leave_balance_crud = CRUDService(StaffLeaveBalance)
        self.leave_type_crud = CRUDService(LeaveType)
        self.accrual_log_crud = CRUDService(LeaveAccrualLog)

    async def approve_leave(
        self,
        db: AsyncSession,
        leave_id: UUID,
        approver_id: UUID,
        approval_status: str,
        notes: str | None = None,
    ):

        leave = await self.leave_crud.get(db, leave_id)
        leave_type = await self.leave_type_crud.get(db, leave.leave_type_id)
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
                # raise HTTPException(400, "Leave balance not initialized")
                # Auto-initialize balance if not found (edge case) future create api schedule job to initialize all balances at year start
                balance = await self.leave_balance_crud.create(
                    db,
                    obj_in={
                        "staff_id": leave.staff_id,
                        "leave_type_id": leave.leave_type_id,
                        "year": leave.start_date.year,
                        "allocated_days": Decimal(leave_type.max_days_per_year or 0),
                        "used_days": Decimal("0"),
                        "remaining_days": Decimal(leave_type.max_days_per_year or 0),
                        "created_by": "system"
                    }
                )
            else :
                balance = balance[0]

            

            # 3️⃣ Deduct balance
            
            leave_type = await self.leave_type_crud.get(db, leave.leave_type_id)

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
            # 4️⃣ Create attendance entries
            # Fetch staff shift once
            shift = await self.shift_crud.get(
                db,
                (await self.staff_crud.get(db, leave.staff_id)).shift_id
            )
            current_date = leave.start_date
            while current_date <= leave.end_date:
                # Skip Holiday
                holiday = await self.holiday_crud.get_by_fields(
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

                existing = await self.attendance_crud.get_by_fields(
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


    async def accrue_monthly_leaves(
        self,
        db: AsyncSession,
        year: int,
        month: int,
    ):
        """
        Accrue monthly leave for all active staff.
        Prevents duplicate runs using LeaveAccrualLog.
        Fully transactional.
        """

        # 1️⃣ Check duplicate accrual
        existing = await self.accrual_log_crud.get_by_fields(
            db,
            fields={
                "year": year,
                "month": month,
            }
        )

        if existing:
            raise HTTPException(
                400,
                f"Accrual already processed for {year}-{month}"
            )

        try:

            # 2️⃣ Fetch leave types with annual allocation
            leave_types = await self.leave_type_crud.get_multi(
                db,
                filters={"is_active": True}
            )

            # 3️⃣ Fetch active staff only
            staff_members = await self.staff_crud.get_multi(
                db,
                filters={"is_active": True},
                limit=100000
            )

            for staff in staff_members:

                # Skip exited staff
                if staff.exit_date:
                    continue

                for lt in leave_types:

                    if not lt.max_days_per_year:
                        continue

                    # 4️⃣ Calculate monthly accrual
                    monthly_accrual = (
                        Decimal(str(lt.max_days_per_year)) / Decimal("12")
                    ).quantize(Decimal("0.01"))

                    balances = await self.leave_balance_crud.get_by_fields(
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
                        await self.leave_balance_crud.create(
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

            # 5️⃣ Create accrual log ONLY AFTER SUCCESS
            await self.accrual_log_crud.create(
                db,
                obj_in={
                    "year": year,
                    "month": month,
                    "status": "completed",
                    "created_by": "system"
                }
            )

            await db.commit()

        except Exception as e:
            await db.rollback()
            raise e

    async def carry_forward_leaves(self, db: AsyncSession, year: int):

        balances = await self.leave_balance_crud.get_multi(
            db,
            limit=100000,
            filters={"year": year}
        )

        for balance in balances:

            leave_type = await self.leave_type_crud.get(db, balance.leave_type_id)

            if not leave_type.carry_forward:
                continue

            carry_days = balance.remaining_days
            existing = await self.leave_balance_crud.get_by_fields(
                db,
                fields={
                    "staff_id": balance.staff_id,
                    "leave_type_id": balance.leave_type_id,
                    "year": year + 1,
                },
            )
            if existing:
                    
                await self.leave_balance_crud.create(
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

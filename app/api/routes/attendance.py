"""
Attendance management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request

# from scipy.fftpack import shift
from app.models.tenant import Shift
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime, timedelta
from datetime import datetime, timezone
from app.models.tenant.staff import StaffProfile
from app.schemas.attendance import (
    AttendanceRecordCreate,
    AttendanceRecordUpdate,
    AttendanceRecordResponse,
    LeaveRequestCreate,
    LeaveRequestUpdate,
    LeaveRequestResponse,
   
)
from app.api.schemas import (
     PaginatedResponse,
    PaginationParams,
    SuccessResponse)
from app.models.tenant import AttendanceRecord, LeaveRequest, LeaveType
from app.db.base import get_db_session
from app.services.attendance import AttendanceService
from app.services.crud import CRUDService
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger
from app.services.leave import LeaveService

logger = get_logger(__name__)
router = APIRouter(prefix="/attendance", tags=["Attendance Management"])

attendance_crud = CRUDService(AttendanceRecord)
leave_crud = CRUDService(LeaveRequest)
leave_type_crud = CRUDService(LeaveType)
staff_crud = CRUDService(StaffProfile)  # Assuming staff_profiles is the table name for staff profiles
attendance_service = AttendanceService()
leave_service = LeaveService()
leave_type_crud = CRUDService(LeaveType)
@router.get("/records", response_model=PaginatedResponse)
async def list_attendance(
    request: Request,
    pagination: PaginationParams = Depends(),
    staff_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List attendance records with filtering."""
    
    filters = {}
    if staff_id:
        filters["staff_id"] = staff_id
    if status:
        filters["status"] = status
    
    total = await attendance_crud.count(db, filters=filters)
    
    records = await attendance_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters,
        order_by="date"
    )
    record_responses = []
    for record in records:
        staff = await staff_crud.get(db, record.staff_id)
        record_responses.append(AttendanceRecordResponse(
            id=record.id,
            staff_id=record.staff_id,
            date=record.date,
            shift_id=record.shift_id,
            status=record.status,
            check_in=record.check_in,
            check_out=record.check_out,
            work_hours=record.work_hours,
            overtime_hours=record.overtime_hours,
            is_manual_entry=record.is_manual_entry,
            approved_by=record.approved_by,
            notes=record.notes,
            created_at=record.created_at,
            updated_at=record.updated_at,
            staff_name=staff.first_name + " " + staff.last_name if staff else None,
        ))
    
    return PaginatedResponse.create(
        items=record_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("/check-in", response_model=AttendanceRecordResponse)
async def check_in(
    request: Request,
    staff_id: UUID,
    location: Optional[dict] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Record staff check-in."""
    user_id = getattr(request.state, 'user_id', None)
    
    record = await attendance_service.check_in(
        db=db,
        staff_id=staff_id,
        user_id=user_id,
        location=location,
    )

    
    logger.info(f"Staff {staff_id} checked in")
    
    return AttendanceRecordResponse(
        id=record.id,
        staff_id=record.staff_id,
        date=record.date,
        shift_id=record.shift_id,
        status=record.status,
        check_in=record.check_in,
        check_out=record.check_out,
        work_hours=record.work_hours,
        overtime_hours=record.overtime_hours,
        is_manual_entry=record.is_manual_entry,
        approved_by=record.approved_by,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at
    )


@router.post("/check-out", response_model=AttendanceRecordResponse)
async def check_out(
    request: Request,
    staff_id: UUID,
    location: Optional[dict] = None,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Record staff check-out."""
    user_id = getattr(request.state, 'user_id', None)   
    record = await attendance_service.check_out(
        db=db,
        staff_id=staff_id,
        user_id=user_id,
        location=location,
        notes=notes,
    )
   
    logger.info(f"Staff {staff_id} checked out")
    
    return AttendanceRecordResponse(
        id=record.id,
        staff_id=record.staff_id,
        date=record.date,
        shift_id=record.shift_id,
        status=record.status,
        check_in=record.check_in,
        check_out=record.check_out,
        work_hours=record.work_hours,
        overtime_hours=record.overtime_hours,
        is_manual_entry=record.is_manual_entry,
        approved_by=record.approved_by,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at
    )


# ============================================
# Leave Routes
# ============================================

@router.get("/leave-requests", response_model=PaginatedResponse)
async def list_leave_requests(
    request: Request,
    pagination: PaginationParams = Depends(),
    staff_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List leave requests with filtering."""
    
    filters = {}
    if staff_id:
        filters["staff_id"] = staff_id
    if status:
        filters["status"] = status
    
    total = await leave_crud.count(db,  filters=filters)
    
    leaves = await leave_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    
    leave_responses = []
    for leave in leaves:
        staff = await staff_crud.get(db, leave.staff_id)
        leave_type = await leave_type_crud.get(db, leave.leave_type_id)
        leave_responses.append(LeaveRequestResponse(
            id=leave.id,
            staff_id=leave.staff_id,
            leave_type_id=leave.leave_type_id,
            start_date=leave.start_date,
            end_date=leave.end_date,
            days_requested=leave.days_requested,
            reason=leave.reason,
            status=leave.status,
            approved_by=leave.approved_by,
            approved_at=leave.approved_at,
            approval_notes=leave.approval_notes,
            documents=leave.documents or [],
            created_at=leave.created_at,
            updated_at=leave.updated_at,
            staff_name=staff.first_name + " " + staff.last_name if staff else None,
            leave_type_name= leave_type.name if leave_type else None
        ))
    
    return PaginatedResponse.create(
        items=leave_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("/leave-requests", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_request(
    request: Request,
    leave_data: LeaveRequestCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new leave request."""
    current_user_id = getattr(request.state, 'user_id', None) 

    leave = await leave_service.create_leave(db, leave_data, current_user_id)
    logger.info(f"Leave request created: {leave.id}")
    
    return LeaveRequestResponse(
        id=leave.id,
        staff_id=leave.staff_id,
        leave_type_id=leave.leave_type_id,
        start_date=leave.start_date,
        end_date=leave.end_date,
        days_requested=leave.days_requested,
        reason=leave.reason,
        status=leave.status,
        approved_by=leave.approved_by,
        approved_at=leave.approved_at,
        approval_notes=leave.approval_notes,
        documents=leave.documents or [],
        created_at=leave.created_at,
        updated_at=leave.updated_at
    )


@router.put("/leave-requests/{leave_id}/approve", response_model=LeaveRequestResponse)
async def approve_leave(
    request: Request,
    leave_id: UUID,
    approval_data: LeaveRequestUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Approve or reject a leave request."""
    user_id = getattr(request.state, 'user_id', None)
    
    # leave = await leave_crud.get(db, leave_id)
    
    # if not leave:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="Leave request not found"
    #     )
    
    # if leave.status != "pending":
    #     raise HTTPException(
    #         status_code=status.HTTP_409_CONFLICT,
    #         detail=f"Leave request already {leave.status}"
    #     )
    # staff_profile = await staff_crud.get_by_user_id(db, user_id)
    # staff_id = staff_profile.id if staff_profile else None
    # # Update leave
    # leave.status = approval_data.status
    # leave.approved_by = staff_id
    # leave.approved_at = datetime.now(timezone.utc)
    # leave.approval_notes = approval_data.approval_notes
    # await db.commit()
    # # await db.flush()
    # await db.refresh(leave)
    # # Publish event
    # if approval_data.status == "approved":
    #     await publish_event(
    #         event_type=EventType.LEAVE_APPROVED,
    #         aggregate_type="leave",
    #         aggregate_id=str(leave.id),
    #         payload={
    #             "staff_id": str(leave.staff_id),
    #             "approved_by": user_id,
    #             "start_date": leave.start_date.isoformat(),
    #             "end_date": leave.end_date.isoformat()
    #         }
    #     )
    leave = await leave_service.approve_leave(
        db=db,
        leave_id=leave_id,
        approver_id=user_id,
        approval_status=approval_data.status,
        notes=approval_data.approval_notes
        )
    logger.info(f"Leave request {leave_id} {approval_data.status}")
    
    return LeaveRequestResponse(
        id=leave.id,
        staff_id=leave.staff_id,
        leave_type_id=leave.leave_type_id,
        start_date=leave.start_date,
        end_date=leave.end_date,
        days_requested=leave.days_requested,
        reason=leave.reason,
        status=leave.status,
        approved_by=leave.approved_by,
        approved_at=leave.approved_at,
        approval_notes=leave.approval_notes,
        documents=leave.documents or [],
        created_at=leave.created_at,
        updated_at=leave.updated_at
    )


@router.get("/leave-types", response_model=List[dict])
async def list_leave_types(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """List all leave types."""
    
    leave_types = await leave_type_crud.get_multi(
        db,
        filters={"is_active": True}
    )
    
    return [
        {
            "id": str(lt.id),
            "name": lt.name,
            "code": lt.code,
            "is_paid": lt.is_paid,
            "color": lt.color,
            "max_days_per_year": lt.max_days_per_year
        }
        for lt in leave_types
    ]


@router.get("/stats")
async def get_attendance_stats(
    request: Request,
    staff_id: Optional[UUID] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Get attendance statistics."""
    
    # Use current month/year if not specified
    now = datetime.now()
    target_month = month or now.month
    target_year = year or now.year
    
    # TODO: Calculate actual statistics from database
    return {
        "month": target_month,
        "year": target_year,
        "staff_id": str(staff_id) if staff_id else None,
        "total_working_days": 22,
        "days_present": 20,
        "days_absent": 1,
        "days_late": 1,
        "half_days": 0,
        "total_work_hours": 160.5,
        "overtime_hours": 5.5,
        "leave_balance": {
            "annual": 15,
            "sick": 8,
            "personal": 3
        }
    }




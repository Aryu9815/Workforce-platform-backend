from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from datetime import datetime, timezone
from app.schemas import (
    AttendanceNotesUpdate,
    AttendanceRecordDetailResponse,
    AttendanceRecordResponse,
    LeaveRequestCreate,
    LeaveRequestUpdate,
    LeaveRequestResponse,
    LeaveTypeRequestCreate,
    LeaveTypeResponse, 
    PaginatedResponse,
    PaginationParams,
    TaskWorkResponse
)
from app.models.tenant import AttendanceRecord
from app.db.base import get_db_session
from app.services.crud import (
    attendance_crud,
    leave_crud,
    leave_type_crud,
    staff_crud
)
from app.core.logging_config import get_logger
from app.services import (
    attendance_service,
    leave_service,
    task_work_service,
    notify
)
from app.utils.rbac_middleware import require_permissions

logger = get_logger(__name__)
router = APIRouter(prefix="/attendance", tags=["Attendance Management"])

@router.get("/records", response_model=PaginatedResponse)
@require_permissions(["attendance:view"])
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
    extra_conditions=[]
    if staff_id:
        filters["staff_id"] = staff_id
    if status:
        filters["status"] = status
    if start_date:
        extra_conditions.append(AttendanceRecord.date >= start_date)

    if end_date:
        extra_conditions.append(AttendanceRecord.date <= end_date)
    total = await attendance_crud.count(db, filters=filters , extra_conditions=extra_conditions)
    
    records = await attendance_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters,
        extra_conditions=extra_conditions ,
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
@require_permissions(["attendance:mark"])
async def check_in(
    request: Request,
    staff_id: UUID,
    location: Optional[dict] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Record staff check-in."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    record = await attendance_service.check_in(
        db=db,
        staff_id=staff_id,
        user_id=user_id,
        location=location,
    )

    
    logger.info(f"Staff {staff_id} checked in")
    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(user_id),
            'title': f"Checked in: {record.date}",
            'message': f"You have checked in for today.\nCheck-in time: {record.check_in.strftime('%H:%M:%S')}",
            }
        )
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
@require_permissions(["attendance:mark"])
async def check_out(
    request: Request,
    staff_id: UUID,
    location: Optional[dict] = None,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Record staff check-out."""
    user_id = getattr(request.state, 'user_id', None)   
    tenant_id = getattr(request.state, 'tenant_id', None)
    record = await attendance_service.check_out(
        db=db,
        staff_id=staff_id,
        user_id=user_id,
        location=location,
        notes=notes,
    )
   
    logger.info(f"Staff {staff_id} checked out")
    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(user_id),
            'title': f"Checked out: {record.date}",
            'message': f"You have checked out for today.\nCheck-out time: {record.check_out.strftime('%H:%M:%S')}",
            }
        )
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
@require_permissions(["leave:view", "leave:view:all"])
async def list_leave_requests(
    request: Request,
    pagination: PaginationParams = Depends(),
    staff_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List leave requests with filtering."""
    user_permissions = getattr(request.state, "permissions", [])
    filters = {}
    if staff_id and "leave:view:all" not in user_permissions:
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
@require_permissions(["leave:create"])
async def create_leave_request(
    request: Request,
    leave_data: LeaveRequestCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new leave request."""
    user_id = getattr(request.state, 'user_id', None) 
    tenant_id = getattr(request.state, 'tenant_id', None)
    leave = await leave_service.create_leave(db, leave_data, user_id)
    logger.info(f"Leave request created: {leave.id}")
    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(user_id),
            'title': "Leave Request Created",
            'message': f"A new leave request has been created for {leave_data.start_date} to {leave_data.end_date}.\nReason: {leave_data.reason or 'No reason provided'}",
            }
        )
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



@router.post("/leave-type", response_model=LeaveTypeResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(["leave-type:create"])
async def create_leave_type(
    request: Request,
    leave_data: LeaveTypeRequestCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new leave type."""
    current_user_id = getattr(request.state, 'user_id', None) 

    leave = await leave_type_crud.create(db, leave_data, current_user_id)
    logger.info(f"Leave type created: {leave.id}")
    
    return LeaveTypeResponse(
        id=leave.id,
        code=leave.code,
        name=leave.name,
        description=leave.description,
        is_paid=leave.is_paid,
        color=leave.color,
        requires_approval=leave.requires_approval,
        max_days_per_year=leave.max_days_per_year,
        carry_forward=leave.carry_forward,
        created_at=leave.created_at,
        updated_at=leave.updated_at
    )

@router.put("/leave-requests/{leave_id}/approve", response_model=LeaveRequestResponse)
@require_permissions(["leave:approve"])
async def approve_leave(
    request: Request,
    leave_id: UUID,
    approval_data: LeaveRequestUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Approve or reject a leave request."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)

    leave = await leave_service.approve_leave(
        db=db,
        leave_id=leave_id,
        approver_id=user_id,
        approval_status=approval_data.status,
        notes=approval_data.approval_notes
    )
    logger.info(f"Leave request {leave_id} {approval_data.status}")

    staff = await staff_crud.get(db, leave.staff_id)
    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(user_id),
            'title': f"Leave Request {approval_data.status.capitalize()}",
            'message': f"You have {approval_data.status} of staff {staff.first_name} {staff.last_name}'s leave request.",
            }
        )
    staff_approver = await staff_crud.get_by_field(db, field="user_id", value=user_id)
    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(staff.user_id),
            'title': f"Leave Request {approval_data.status.capitalize()}",
            'message': f"Your leave request has been {approval_data.status} by {staff_approver.first_name} {staff_approver.last_name}.",
            }
        )
    
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
@require_permissions(["leave-type:view"])
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



@router.get("/task-sessions/attendance/{attendance_id}", response_model=List[TaskWorkResponse])
@require_permissions(["attendance:view"])
async def get_sessions_by_attendance(
    attendance_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get task sessions linked to an attendance record."""
    
    sessions = await attendance_service.get_task_sessions_by_attendance(
        db=db,
        attendance_id=attendance_id
    )
    
    return [TaskWorkResponse.from_orm(s) for s in sessions]


@router.get("/{attendance_id}" , response_model=AttendanceRecordDetailResponse)
@require_permissions(["attendance:view"])
async def get_attendance_record(
    request: Request,  #  REQUIRED
    attendance_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get attendance record details."""
    
    record = await attendance_crud.get(db, attendance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    staff = await staff_crud.get(db, record.staff_id)
    task_work = await task_work_service.get_sessions_by_attendance(db, record.id)
    return AttendanceRecordDetailResponse(
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

        task_work_sessions=[TaskWorkResponse.from_orm(s) for s in task_work] or [],
        created_at=record.created_at,
        updated_at=record.updated_at,
        staff_name=staff.first_name + " " + staff.last_name if staff else None,
    )

@router.put("/records/{attendance_id}", response_model=AttendanceRecordResponse)
@require_permissions(["attendance:mark"])
async def update_attendance_notes(
    request: Request,
    attendance_id: UUID,
    payload: AttendanceNotesUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update only notes of an attendance record."""
    user_id = getattr(request.state, "user_id", None)
    record = await attendance_crud.get(db, attendance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    record.notes = payload.notes
    record.updated_at = datetime.now(timezone.utc)
    record.updated_by = user_id
    db.add(record)
    await db.commit()
    await db.refresh(record)

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
        updated_at=record.updated_at,
    )
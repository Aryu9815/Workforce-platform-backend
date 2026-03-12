from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
from app.db.base import get_db_session
from app.schemas import (
    TaskWorkStartRequest,
    TaskWorkResponse,
    SuccessResponse
)
from app.services.crud import staff_crud
from app.services import task_work_service
from app.utils.rbac_middleware import require_permissions
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/task-work", tags=["Task Work Tracking"])

# ==========================================================
# START / SWITCH TASK
# ==========================================================

@router.post(
    "/start",
    response_model=TaskWorkResponse,
    status_code=status.HTTP_201_CREATED
)
@require_permissions(["attendance:mark"])
async def start_task_work(
    request: Request,
    payload: TaskWorkStartRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Start or switch task work session.
    If active session exists → auto-switch.
    """

    user_id = getattr(request.state, "user_id", None)
    staff = await  staff_crud.get_by_field(db, field="user_id", value=user_id)
    staff_id = staff.id
    session = await task_work_service.switch_task(
        db=db,
        staff_id=staff_id,
        task_id=payload.task_id,
        user_id=user_id,
    )

    logger.info(f"Task session started/switched: {session.id}")

    return TaskWorkResponse.from_orm(session)


# ==========================================================
# STOP CURRENT TASK (Manual Stop)
# ==========================================================

@router.post(
    "/stop",
    response_model=SuccessResponse
)
@require_permissions(["attendance:mark"])
async def stop_task_work(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Stop current active task session.
    """

    user_id = getattr(request.state, "user_id", None)
    staff = await  staff_crud.get_by_field(db, field="user_id", value=user_id)
    staff_id = staff.id

    await task_work_service.end_day(
        db=db,
        staff_id=staff_id,
        user_id=user_id,
    )

    logger.info(f"Task session stopped for staff {staff_id}")

    return SuccessResponse(message="Task session stopped successfully")


# ==========================================================
# LIST MY TODAY SESSIONS
# ==========================================================

@router.get(
    "/my-sessions",
    response_model=List[TaskWorkResponse]
)
@require_permissions(["attendance:view"])
async def get_my_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get today's task sessions for logged-in user.
    """
    user_id = getattr(request.state, "user_id", None)
    staff = await  staff_crud.get_by_field(db, field="user_id", value=user_id)
    staff_id = staff.id

    sessions = await task_work_service.get_today_sessions(
        db=db,
        staff_id=staff_id
    )

    return [TaskWorkResponse.from_orm(s) for s in sessions]


# ==========================================================
# GET SESSIONS BY ATTENDANCE
# ==========================================================

@router.get(
    "/attendance/{attendance_id}",
    response_model=List[TaskWorkResponse]
)
@require_permissions(["attendance:view"])
async def get_sessions_by_attendance(
    attendance_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all sessions for a specific attendance record.
    """

    sessions = await task_work_service.get_sessions_by_attendance(
        db=db,
        attendance_id=attendance_id
    )

    return [TaskWorkResponse.from_orm(s) for s in sessions]
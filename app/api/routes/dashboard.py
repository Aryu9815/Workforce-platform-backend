from fastapi import APIRouter, Depends, Request , Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import  Optional
from datetime import date
from app.core.logging_config import get_logger
from app.services.dashboard.dashboard_analytics import DashboardAnalyticsService
from app.db.base import get_db_session
from app.services.dashboard.dashboard_service import DashboardService
from app.schemas import DashboardOverviewResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get(
    "/admin/overview",
    response_model=DashboardOverviewResponse
)
# @require_permissions(["dashboard:view"])
async def get_admin_dashboard_overview(
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Admin Dashboard Overview

    Returns aggregated system-wide summary:
    - HR Summary
    - Attendance Summary
    - Leave Summary
    - Project Summary
    - Task Summary
    - Finance Summary
    """

    user_id = getattr(request.state, "user_id", None)

    logger.info(
        f"Admin dashboard requested by user={user_id} "
        f"range=({start_date} - {end_date})"
    )

    dashboard_service = DashboardService(db)

    overview = await dashboard_service.get_overview(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    return DashboardOverviewResponse(**overview)

@router.get("/admin/charts/attendance-trend")
# @require_permissions(["dashboard:view"])
async def attendance_trend(
    request: Request,
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Monthly attendance trend (chart-ready).
    """

    service = DashboardAnalyticsService(db)
    data = await service.attendance_trend(months)

    return {
        "chart": "attendance_trend",
        "interval": "monthly",
        "months": months,
        "data": data
    }


@router.get("/admin/charts/leave-trend")
# @require_permissions(["dashboard:view"])
async def leave_trend(
    request: Request,
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Monthly leave request trend.
    """

    service = DashboardAnalyticsService(db)
    data = await service.leave_trend(months)

    return {
        "chart": "leave_trend",
        "interval": "monthly",
        "months": months,
        "data": data
    }

@router.get("/admin/charts/project-cost-trend")
# @require_permissions(["dashboard:view"])
async def project_cost_trend(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Monthly project budget vs actual cost trend.
    """

    service = DashboardAnalyticsService(db)
    data = await service.project_cost_trend()

    return {
        "chart": "project_cost_trend",
        "interval": "monthly",
        "data": data
    }


@router.get("/admin/charts/task-completion-trend")
# @require_permissions(["dashboard:view"])
async def task_completion_trend(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Monthly completed task trend.
    """

    service = DashboardAnalyticsService(db)
    data = await service.task_completion_trend()

    return {
        "chart": "task_completion_trend",
        "interval": "monthly",
        "data": data
    }

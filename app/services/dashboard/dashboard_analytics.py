from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import AttendanceRecord, LeaveRequest, Project, Task


class DashboardAnalyticsService:
    """
    Dashboard Analytics Service
    Provides chart-ready grouped analytics data.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================================
    # Attendance Trend (Monthly)
    # ==========================================================
    async def attendance_trend(self, months: int):

        start_date = datetime.now(timezone.utc) - timedelta(days=months * 30)

        month_expr = func.date_trunc(
            "month",
            AttendanceRecord.date
        ).label("month")

        stmt = (
            select(
                month_expr,
                func.count(AttendanceRecord.id).label("total_records"),
                func.coalesce(
                    func.sum(AttendanceRecord.overtime_hours), 0
                ).label("total_overtime")
            )
            .where(AttendanceRecord.date >= start_date)
            .group_by(month_expr)
            .order_by(desc(month_expr))
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "month": row.month.strftime("%Y-%m"),
                "total_records": row.total_records,
                "total_overtime": float(row.total_overtime),
            }
            for row in rows
        ]

    # ==========================================================
    # Leave Trend (Monthly)
    # ==========================================================
    async def leave_trend(self, months: int):

        start_date = datetime.now(timezone.utc) - timedelta(days=months * 30)

        month_expr = func.date_trunc(
            "month",
            LeaveRequest.start_date
        ).label("month")

        stmt = (
            select(
                month_expr,
                func.count(LeaveRequest.id).label("leave_requests"),
            )
            .where(LeaveRequest.start_date >= start_date)
            .group_by(month_expr)
            .order_by(desc(month_expr))
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "month": row.month.strftime("%Y-%m"),
                "leave_requests": row.leave_requests,
            }
            for row in rows
        ]

    # ==========================================================
    # Project Cost Trend (Monthly)
    # ==========================================================
    async def project_cost_trend(self, months: int = 6):

        start_date = datetime.now(timezone.utc) - timedelta(days=months * 30)

        month_expr = func.date_trunc(
            "month",
            Project.created_at
        ).label("month")

        stmt = (
            select(
                month_expr,
                func.coalesce(func.sum(Project.actual_cost), 0).label("actual_cost"),
                func.coalesce(func.sum(Project.budget), 0).label("budget"),
            )
            .where(Project.created_at >= start_date)
            .group_by(month_expr)
            .order_by(desc(month_expr))
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "month": row.month.strftime("%Y-%m"),
                "actual_cost": float(row.actual_cost),
                "budget": float(row.budget),
            }
            for row in rows
        ]

    # ==========================================================
    # Task Completion Trend (Monthly)
    # ==========================================================
    async def task_completion_trend(self, months: int = 6):

        start_date = datetime.now(timezone.utc) - timedelta(days=months * 30)

        month_expr = func.date_trunc(
            "month",
            Task.completed_at
        ).label("month")

        stmt = (
            select(
                month_expr,
                func.count(Task.id).label("completed_tasks"),
            )
            .where(
                Task.completed_at.isnot(None),
                Task.completed_at >= start_date,
            )
            .group_by(month_expr)
            .order_by(desc(month_expr))
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "month": row.month.strftime("%Y-%m"),
                "completed_tasks": row.completed_tasks,
            }
            for row in rows
        ]
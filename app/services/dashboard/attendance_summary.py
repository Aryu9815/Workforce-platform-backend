# services/dashboard/attendance_summary.py

from sqlalchemy import select, func, case
from app.models.tenant import AttendanceRecord

class AttendanceSummaryService:

    def __init__(self, db):
        self.db = db

    async def get_summary(self, context):
        stmt = select(
            func.count(case((AttendanceRecord.status == "present", 1))).label("present"),
            func.count(case((AttendanceRecord.status == "late", 1))).label("late"),
            func.count(case((AttendanceRecord.status == "absent", 1))).label("absent"),
            func.sum(AttendanceRecord.overtime_hours).label("overtime_hours")
        ).where(
            AttendanceRecord.date == context.today
        )

        result = await self.db.execute(stmt)
        return dict(result.one()._mapping)
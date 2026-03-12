# services/dashboard/leave_summary.py

from sqlalchemy import select, func, case
from app.models.tenant import LeaveRequest

class LeaveSummaryService:

    def __init__(self, db):
        self.db = db

    async def get_summary(self, context):
        stmt = select(
            func.count(case((LeaveRequest.status == "pending", 1))).label("pending"),
            func.count(
                case(
                    (
                        (LeaveRequest.start_date <= context.today) &
                        (LeaveRequest.end_date >= context.today),
                        1
                    )
                )
            ).label("on_leave_today")
        )

        result = await self.db.execute(stmt)
        return dict(result.one()._mapping)

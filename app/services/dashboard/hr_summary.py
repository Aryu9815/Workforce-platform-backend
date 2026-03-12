# services/dashboard/hr_summary.py

from sqlalchemy import select, func, case
from app.models.tenant import StaffProfile

class HRSummaryService:

    def __init__(self, db):
        self.db = db

    async def get_summary(self):
        stmt = select(
            func.count(StaffProfile.id).label("total_staff"),
            func.count(
                case((StaffProfile.exit_date.is_(None), 1))
            ).label("active_staff")
        )

        result = await self.db.execute(stmt)
        return dict(result.one()._mapping)
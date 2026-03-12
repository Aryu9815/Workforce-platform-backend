# services/dashboard/project_summary.py

from sqlalchemy import select, func, case
from app.models.tenant import Project

class ProjectSummaryService:

    def __init__(self, db):
        self.db = db

    async def get_summary(self):
        stmt = select(
            func.count(case((Project.is_active == True, 1))).label("active_projects"),
            func.sum(Project.budget).label("total_budget"),
            func.sum(Project.actual_cost).label("actual_cost")
        )

        result = await self.db.execute(stmt)
        return dict(result.one()._mapping)
# services/dashboard/task_summary.py

from sqlalchemy import select, func, case
from datetime import date
from app.models.tenant import Task

class TaskSummaryService:

    def __init__(self, db):
        self.db = db

    async def get_summary(self):
        today = date.today()

        stmt = select(
            func.count(Task.id).label("total_tasks"),
            func.count(case((Task.completed_at.is_(None), 1))).label("open_tasks"),
            func.count(
                case(
                    (
                        (Task.due_date < today) &
                        (Task.completed_at.is_(None)),
                        1
                    )
                )
            ).label("overdue_tasks")
        )

        result = await self.db.execute(stmt)
        return dict(result.one()._mapping)
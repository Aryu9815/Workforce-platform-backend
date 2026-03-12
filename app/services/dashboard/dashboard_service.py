# services/dashboard/dashboard_service.py

from .base import DashboardContext
from .hr_summary import HRSummaryService
from .attendance_summary import AttendanceSummaryService
from .leave_summary import LeaveSummaryService
from .project_summary import ProjectSummaryService
from .task_summary import TaskSummaryService
from .finance_summary import FinanceSummaryService

class DashboardService:

    def __init__(self, db):
        self.db = db

    async def get_overview(self, user_id, start_date=None, end_date=None):

        context = DashboardContext(user_id, start_date, end_date)

        return {
            "hr": await HRSummaryService(self.db).get_summary(),
            "attendance": await AttendanceSummaryService(self.db).get_summary(context),
            "leave": await LeaveSummaryService(self.db).get_summary(context),
            "project": await ProjectSummaryService(self.db).get_summary(),
            "task": await TaskSummaryService(self.db).get_summary(),
            "finance": await FinanceSummaryService(self.db).get_summary(context),
        }
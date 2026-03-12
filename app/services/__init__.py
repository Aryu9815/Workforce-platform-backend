"""Services module initialization."""
from app.services.auth import auth_service
from app.services.task_work_service import task_work_service
from app.services.dashboard import dashboard_service, dashboard_analytics
from app.services.attendance import attendance_service
from app.services.leave_initialization_service import leave_initialization_service
from app.services.leave import leave_service
from app.services.notification import notify
from app.services.projects import project_service
from app.services.sprints import sprint_service
from app.services.staff import staff_service
from app.services.task_work_service import task_work_service
from app.services.task import task_service
from app.services.team import team_service
from app.services.workflow import workflow_service


"""API routes module initialization."""
from app.api.routes.auth import router as auth_router
from app.api.routes.staff import router as staff_router
from app.api.routes.projects import router as projects_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.attendance import router as attendance_router
from app.api.routes.reimbursements import router as reimbursements_router
from app.api.routes.workflow import router as workflow_router
from app.api.routes.assets import router as  assets_router
from app.api.routes.sprint import router as sprint_router
from app.api.routes.permission_role import router as permission_role_router
from app.api.routes.roles import router as role_router
from app.api.routes.permissions import router as permission_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.task_work_routes import router as task_work_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.ai_routes import router as ai_router
from app.api.routes.task_label import router as task_label_router

__all__ = [
    "auth_router",
    "staff_router",
    "projects_router",
    "tasks_router",
    "attendance_router",
    "reimbursements_router",
    "workflow_router",
    "assets_router",
    "permission_role_router",
    "sprint_router",
    "permission_router",
    "role_router",
    "notifications_router",
    "task_work_router",
    "dashboard_router",
    "ai_router",
    "task_label_router",
]

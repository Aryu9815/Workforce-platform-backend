"""API routes module initialization."""
from app.api.routes.auth import router as auth_router
from app.api.routes.staff import router as staff_router
from app.api.routes.projects import router as projects_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.attendance import router as attendance_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.reimbursements import router as reimbursements_router
from app.api.routes.workflow import router as workflow_router
from app.api.routes.assets import router as  assets_router
__all__ = [
    "auth_router",
    "staff_router",
    "projects_router",
    "tasks_router",
    "attendance_router",
    "inventory_router",
    "reimbursements_router",
    "workflow_router",
    "assets_router"
]

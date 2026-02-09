"""API module initialization."""
from app.api.routes import (
    auth_router,
    staff_router,
    projects_router,
    tasks_router,
    attendance_router,
    inventory_router,
    reimbursements_router,
)
from app.api.schemas import (
    SuccessResponse,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
)

__all__ = [
    "auth_router",
    "staff_router",
    "projects_router",
    "tasks_router",
    "attendance_router",
    "inventory_router",
    "reimbursements_router",
    "SuccessResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationParams",
]

"""Middleware module initialization."""
from app.middleware.auth import (
    AuthMiddleware,
    TenantResolutionMiddleware,
    LoggingMiddleware,
    get_current_user_id,
    get_current_tenant_id,
    get_current_user_permissions,
    require_permissions,
)
from app.middleware.rate_limit import RateLimitMiddleware, RateLimiter
from app.middleware.error_handler import ErrorHandlerMiddleware, add_exception_handlers

__all__ = [
    "AuthMiddleware",
    "TenantResolutionMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "RateLimiter",
    "ErrorHandlerMiddleware",
    "add_exception_handlers",
    "get_current_user_id",
    "get_current_tenant_id",
    "get_current_user_permissions",
    "require_permissions",
]

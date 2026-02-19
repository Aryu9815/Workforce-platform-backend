"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import redis.asyncio as redis
import logging
from starlette.middleware import Middleware
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.db.base import db_manager
from app.events import register_event_handlers
from app.core.scheduler import scheduler, monthly_accrual_job

from app.middleware import (
    AuthMiddleware,
    TenantResolutionMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    ErrorHandlerMiddleware,
    add_exception_handlers,
)
from app.api.routes import (
    auth_router,
    staff_router,
    projects_router,
    tasks_router,
    attendance_router,
    reimbursements_router,
    workflow_router,
    assets_router,
    sprint_router,
)

# Setup logging
loggers = setup_logging()
logger = get_logger(__name__)


# Redis client (initialized in lifespan)
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database
    db_manager.init_engine()
    logger.info("Database engine initialized")
    
    # Initialize Redis
    global redis_client
    try:
        redis_client = redis.from_url(
            str(settings.REDIS_URL),
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without caching.")
        redis_client = None
    
    # Register event handlers
    register_event_handlers()
    logger.info("Event handlers registered")
    # ✅ START SCHEDULER HERE
    scheduler.add_job(
        monthly_accrual_job,
        trigger="cron",
        day=1,
        hour=0,
        minute=5,
    )
    scheduler.start()
    logger.info("Scheduler started")
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    scheduler.shutdown()
    logger.info("Scheduler stopped")

    # Close database connections
    await db_manager.close()
    logger.info("Database connections closed")
    
    # Close Redis connection
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    Middleware(ErrorHandlerMiddleware),
    Middleware(LoggingMiddleware),
    Middleware(TenantResolutionMiddleware),
    Middleware(AuthMiddleware),
    Middleware(RateLimitMiddleware),
]

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-Tenant Project, Workforce & Operations Management Platform",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
    middleware=middleware  # Add CORS middleware
)

# Add exception handlers
add_exception_handlers(app)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# API version prefix
API_V1_PREFIX = "/api/v1"

# Include routers
app.include_router(auth_router, prefix=f"{API_V1_PREFIX}")
app.include_router(staff_router, prefix=f"{API_V1_PREFIX}")
app.include_router(projects_router, prefix=f"{API_V1_PREFIX}")
app.include_router(tasks_router, prefix=f"{API_V1_PREFIX}")
app.include_router(attendance_router, prefix=f"{API_V1_PREFIX}")
app.include_router(reimbursements_router, prefix=f"{API_V1_PREFIX}")
app.include_router(workflow_router, prefix=f"{API_V1_PREFIX}")
app.include_router(assets_router , prefix=f"{API_V1_PREFIX}")
app.include_router(sprint_router, prefix=f"{API_V1_PREFIX}")



# Dashboard endpoint
@app.get(f"{API_V1_PREFIX}/dashboard", tags=["Dashboard"])
async def get_dashboard_stats(request: Request):
    """Get dashboard statistics."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    # TODO: Calculate actual statistics from database
    return {
        "success": True,
        "data": {
            "total_staff": 0,
            "total_projects": 0,
            "active_tasks": 0,
            "pending_leaves": 0,
            "pending_reimbursements": 0,
            "low_stock_items": 0,
            "attendance_today": {
                "present": 0,
                "absent": 0,
                "late": 0,
                "on_leave": 0
            },
            "recent_activities": []
        }
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "documentation": "/docs" if settings.DEBUG else None,
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

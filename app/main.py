"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.middleware import Middleware
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.db.base import db_manager
from app.core.redis_manager import redis_manager
from app.core.scheduler import scheduler, monthly_accrual_job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.utils.notification_worker import process_pending_jobs, notification_cleaner, task_alert_job
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
    permission_role_router,
    role_router,
    permission_router,
    notifications_router,
    task_work_router,
    dashboard_router,
    ai_router,
    task_label_router,
)
from dotenv import load_dotenv

# Setup logging
loggers = setup_logging()
logger = get_logger(__name__)


scheduler = AsyncIOScheduler()
scheduler_started = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database
    db_manager.init_engine()
    logger.info("Database engine initialized")
    
    success = await redis_manager.connect()
    if not success:
        logger.warning("Redis connection failed. Running without caching.")
    
    # START SCHEDULER HERE
    scheduler.add_job(
        monthly_accrual_job,
        trigger="cron",
        day=1,
        hour=0,
        minute=5,
    )
    scheduler.add_job(process_pending_jobs, "interval", seconds=10)
    scheduler.add_job(
        notification_cleaner,
        "cron",
        hour=2,
    )
    scheduler.add_job(
        task_alert_job,
        trigger="cron",
        hour=10,
        minute=0,
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
    await redis_manager.clear_cache()
    await redis_manager.close()
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
load_dotenv()

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
app.include_router(permission_role_router , prefix=f"{API_V1_PREFIX}" )
app.include_router(permission_router , prefix=f"{API_V1_PREFIX}" )
app.include_router(role_router , prefix=f"{API_V1_PREFIX}" )
app.include_router(notifications_router , prefix=f"{API_V1_PREFIX}" )
app.include_router(task_work_router , prefix=f"{API_V1_PREFIX}" )
app.include_router(dashboard_router , prefix=f"{API_V1_PREFIX}" )
app.include_router(ai_router , prefix=f"{API_V1_PREFIX}" )
app.include_router(task_label_router , prefix=f"{API_V1_PREFIX}" )


# Dashboard endpoint
@app.get(f"{API_V1_PREFIX}/dashboard", tags=["Dashboard"])
async def get_dashboard_stats(request: Request):
    """Get dashboard statistics."""
    
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

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession,async_sessionmaker , AsyncEngine
from typing import Callable
from typing import Callable, Dict, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.sql import select
from app.models.common.tenant_configuration import TenantConfiguration
from app.core.logging_config import get_logger
import asyncio
from app.core.config import settings
from sqlalchemy import event
import logging
import time

sql_logger = logging.getLogger("sql_logger")
logger = get_logger(__name__)

_tenant_engine_cache: Dict[str, Tuple[AsyncEngine, async_sessionmaker]] = {}
_cache_lock: Optional[asyncio.Lock] = None

def _get_cache_lock():
    """Lazy initialization of cache lock to avoid event loop issues"""
    global _cache_lock
    if _cache_lock is None:
        try:
            _cache_lock = asyncio.Lock()
        except RuntimeError:
            # If no event loop exists, create a new one (shouldn't happen in FastAPI context)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            _cache_lock = asyncio.Lock()
    return _cache_lock


async def get_tenant_session(db: AsyncSession, tenant_uuid: str) -> Callable[..., AsyncSession]:
    logger.info(f"Getting tenant session for tenant {tenant_uuid}")
    
    # Check cache first (fast path)
    if settings.CACHE_DB=="YES":
        cache_lock = _get_cache_lock()
        async with cache_lock:
            if tenant_uuid in _tenant_engine_cache:
                logger.info(f"Using cached engine for tenant {tenant_uuid}")
                _, session_maker = _tenant_engine_cache[tenant_uuid]
                print("Using cached tenant DB engine")
                return session_maker
    else:
        print("Caching is Disabled")
    
    # If not in cache, fetch tenant configuration (outside lock to avoid blocking)
    tenant = await db.execute(
        select(TenantConfiguration).filter(
            TenantConfiguration.tenant_uuid == str(tenant_uuid),
            TenantConfiguration.is_active == True,
        )
    )
    tenant = tenant.scalars().first()
    if not tenant:
        logger.error(f"Tenant {tenant_uuid} not found")
        raise HTTPException(status_code=400, detail="Tenant not found")

    database = tenant.env_config['database']
    db_url = (
        f"postgresql+asyncpg://{database['username']}:{database['password']}"
        f"@{database['host']}:{database['port']}/{database['database_name']}"
    )

    async_engine = create_async_engine(
        db_url,
        pool_recycle=180,
    )

    # Add event listener for SQL logging
    @event.listens_for(async_engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(async_engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        try:
            duration = (time.time() - context._query_start_time) * 1000  # ms
            
            # TRUNCATE very long statements (to avoid huge logs)
            truncated_statement = (
                statement if len(statement) < 500 else statement[:500] + " ...[truncated]"
            )

            sql_logger.info(
                f"[{duration:.2f} ms] SQL: {truncated_statement} | Params: {parameters}"
            )

            # Optional: Slow query warning
            if duration > 500:  # e.g., >0.5 seconds
                sql_logger.warning(
                    f"SLOW QUERY ({duration:.2f} ms): {truncated_statement}"
                )

        except Exception as e:
            sql_logger.error(f"SQL logging failed: {str(e)}")

    async_session_maker = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    
    # Double-check locking: Check cache again before storing (prevent race condition)
    if settings.CACHE_DB=="YES":
        async with cache_lock:
            # Another request might have created and cached the engine while we were creating ours
            if tenant_uuid in _tenant_engine_cache:
                # Use the cached one and dispose the one we just created
                logger.info(f"Another request cached engine for tenant {tenant_uuid}, using cached version")
                await async_engine.dispose()  # Dispose the duplicate engine
                _, session_maker = _tenant_engine_cache[tenant_uuid]
                return session_maker
            
            # Store in cache (engine and session maker)
            _tenant_engine_cache[tenant_uuid] = (async_engine, async_session_maker)
            logger.info(f"Cached engine for tenant {tenant_uuid}")
    
    return async_session_maker

async def close_all_tenant_engines():
    """
    Close and dispose all cached tenant engines.
    Should be called on application shutdown.
    """
    cache_lock = _get_cache_lock()
    async with cache_lock:
        if not _tenant_engine_cache:
            logger.info("No tenant engines to close")
            return
        
        logger.info(f"Closing {len(_tenant_engine_cache)} tenant engines")
        for tenant_uuid, (engine, session_maker) in _tenant_engine_cache.items():
            try:
                if engine:
                    await engine.dispose()
                    logger.info(f"Disposed engine for tenant {tenant_uuid}")
            except Exception as e:
                logger.error(f"Error disposing engine for tenant {tenant_uuid}: {e}")
        
        _tenant_engine_cache.clear()
        logger.info("All tenant engines closed and cache cleared")
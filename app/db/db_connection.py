from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine ,  async_sessionmaker , AsyncEngine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import MetaData
from app.core.config import settings
from sqlalchemy import Column, Boolean,func,TIMESTAMP, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from typing import Optional, Tuple
import asyncio
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# DATABASE_URL = str(settings.DATABASE_URL)
print(type(settings.DATABASE_URL))
print(settings.DATABASE_URL)
# Cache for common database engine and session maker
# Store as tuple: (engine, session_maker)
_common_engine_cache: Optional[Tuple[AsyncEngine, async_sessionmaker]] = None
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


async def get_common_engine_and_session() -> Tuple[AsyncEngine, async_sessionmaker]:
    """
    Get or create the common database engine and session maker with caching.
    Uses double-check locking pattern for thread-safe initialization.
    """
    if settings.CACHE_DB=="YES":
        global _common_engine_cache
        # Check cache first (fast path)
        cache_lock = _get_cache_lock()
        async with cache_lock:
            if _common_engine_cache is not None:
                logger.info("Using cached common database engine")
                print("Using cached Common DB engine")
                return _common_engine_cache
    else:
        print("Caching is Disabled")
    # If not in cache, create engine (outside lock to avoid blocking)
    async_engine = create_async_engine(
        str(settings.DATABASE_URL),
        pool_recycle=180,
    )
    
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    # Double-check locking: Check cache again before storing (prevent race condition)
    if settings.CACHE_DB=="YES":
        async with cache_lock:
            # Another request might have created and cached the engine while we were creating ours
            if _common_engine_cache is not None:
                # Use the cached one and dispose the one we just created
                logger.info("Another request cached common engine, using cached version")
                await async_engine.dispose()  # Dispose the duplicate engine
                return _common_engine_cache
            
            # Store in cache (engine and session maker)
            _common_engine_cache = (async_engine, async_session_maker)
            logger.info("Cached common database engine")
    
    return (async_engine, async_session_maker)

async def get_common_session_maker() -> async_sessionmaker:
    """
    Get the common database session maker (convenience function).
    """
    _, session_maker = await get_common_engine_and_session()
    return session_maker


async def close_common_engine():
    """
    Close and dispose the cached common database engine.
    Should be called on application shutdown.
    """
    cache_lock = _get_cache_lock()
    async with cache_lock:
        global _common_engine_cache
        if _common_engine_cache is None:
            logger.info("No common engine to close")
            return
        
        engine, _ = _common_engine_cache
        try:
            if engine:
                await engine.dispose()
                logger.info("Disposed common database engine")
        except Exception as e:
            logger.error(f"Error disposing common engine: {e}")
        
        _common_engine_cache = None
        logger.info("Common engine closed and cache cleared")
# Metadata for each schema
CommonMetadata = MetaData()
TenantMetadata = MetaData()

# Declarative bases for each schema
TenantBase = declarative_base(metadata=TenantMetadata)
CommonBase = declarative_base(metadata=CommonMetadata)

class TenantScopedMixin:
    
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(255),nullable=False)
    updated_by = Column(String(255))

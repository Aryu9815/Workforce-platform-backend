"""
Base database configuration and session management.
"""
from typing import AsyncGenerator, Optional
from contextvars import ContextVar
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
import logging
import time
from app.core.config import settings
from app.db.db_connection import get_common_session_maker
from fastapi import Depends, HTTPException, Request

from app.db.tenant_connection import get_tenant_session

# SQLAlchemy Base
Base = declarative_base()

# Context variable for tenant ID
tenant_id_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)

# Logger for SQL queries
sql_logger = logging.getLogger("sql_logger")


# class TenantAwareQueryMixin:
#     """Mixin to automatically filter queries by tenant_id."""
    
#     @classmethod
#     def filter_by_tenant(cls, query, tenant_id: Optional[str] = None):
#         """Filter query by tenant_id if the model has tenant_id column."""
#         if hasattr(cls, 'tenant_id'):
#             if tenant_id is None:
#                 tenant_id = tenant_id_ctx.get()
#             if tenant_id:
#                 return query.filter(cls.tenant_id == tenant_id)
#         return query


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.async_session_maker: Optional[async_sessionmaker] = None
    
    def init_engine(self):
        """Initialize the async database engine."""
        self.engine = create_async_engine(
            str(settings.DATABASE_URL),
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            pool_pre_ping=True,
            echo=False,
        )
        
        # Add event listener for SQL logging
        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
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
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    
    async def close(self):
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
    
    async def create_tables(self):
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self):
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# Global database manager instance
db_manager = DatabaseManager()


# async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
#     """
#     Dependency for getting database sessions.
#     Usage: Depends(get_db_session)
#     """
#     async with db_manager.async_session_maker() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise
#         finally:
#             await session.close()

async def get_common_db(request: Request=None):
    session_maker = await get_common_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            print("Common DB - Session Close - Starting")
            await session.close()
            print("Common DB - Session Close - Completed")

async def get_db_session(
    request: Request,
    common_db: AsyncSession = Depends(get_common_db),
):
    tenant_uuid: str = getattr(request.state, "tenant_id", None)

    if not tenant_uuid:
        raise HTTPException(status_code=400, detail="Tenant not resolved")

    async_session_maker = await get_tenant_session(common_db, tenant_uuid)

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            print("Closing session")
            await session.close()
            print("Closed session")


def set_tenant_context(tenant_id: str):
    """Set the tenant ID in the context variable."""
    tenant_id_ctx.set(tenant_id)


def get_tenant_context() -> Optional[str]:
    """Get the current tenant ID from context."""
    return tenant_id_ctx.get()


def clear_tenant_context():
    """Clear the tenant ID from context."""
    tenant_id_ctx.set(None)

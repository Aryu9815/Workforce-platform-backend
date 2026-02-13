"""
Reusable CRUD service layer for database operations.
"""
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic CRUD service with multi-tenancy support.
    
    Usage:
        crud_user = CRUDService(User, UserCreate, UserUpdate)
    """
    
    def __init__(
        self,
        model: Type[ModelType],
        create_schema: Type[CreateSchemaType] = None,
        update_schema: Type[UpdateSchemaType] = None
    ):
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
    
    def _apply_soft_delete_filter(self, query, include_deleted: bool = False):
        """Apply soft delete filter to query."""
        if hasattr(self.model, 'is_deleted') and not include_deleted:
            query = query.where(self.model.is_deleted.is_(False))
        return query
   
    def _apply_is_active_filter(self, query, include_inactive: bool = False):
        """Apply soft delete filter to query."""
        if hasattr(self.model, 'is_active') and not include_inactive:
            query = query.where(self.model.is_active.is_(True))
        return query
    
    async def get(
        self,
        db: AsyncSession,
        id: Union[str, UUID],
         
        include_deleted: bool = False,
        include_inactive: bool = False
    ) -> Optional[ModelType]:
        """Get a single record by ID."""
        query = select(self.model).where(self.model.id == id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_is_active_filter(query, include_inactive)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    async def get_by_user_id(
        self,
        db: AsyncSession,
        user_id: Union[str, UUID],
        include_deleted: bool = False,
        include_inactive: bool = False
    ) -> Optional[ModelType]:
        """Get a single record by user_id."""
        query = select(self.model).where(self.model.user_id == user_id)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_is_active_filter(query, include_inactive)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()  
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
         
        include_deleted: bool = False,
        include_inactive: bool = False,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_is_active_filter(query, include_inactive)
        
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)
        
        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            query = query.order_by(getattr(self.model, order_by))
        elif hasattr(self.model, 'created_at'):
            query = query.order_by(self.model.created_at.desc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def count(
        self,
        db: AsyncSession,
         
        include_deleted: bool = False,
        include_inactive: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count records."""
        query = select(func.count(self.model.id))
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_is_active_filter(query, include_inactive)

        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)
        
        result = await db.execute(query)
        return result.scalar()
    
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
        additional_data: Optional[Dict[str, Any]] = None
    ) -> ModelType:
        """Create a new record."""
        if isinstance(obj_in, dict):
            obj_data = obj_in.copy()
        else:
            obj_data = obj_in.model_dump(exclude_unset=True)
        
        
        # Add additional data
        if additional_data:
            obj_data.update(additional_data)
        
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        
        logger.info(f"Created {self.model.__name__} with id {db_obj.id}")
        return db_obj
    
    async def create_many(
        self,
        db: AsyncSession,
        *,
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]],
    ) -> List[ModelType]:
        """Create multiple records."""
        db_objs = []
        
        for obj_in in objs_in:
            if isinstance(obj_in, dict):
                obj_data = obj_in.copy()
            else:
                obj_data = obj_in.model_dump(exclude_unset=True)
            
            
            
            db_objs.append(self.model(**obj_data))
        
        db.add_all(db_objs)
        await db.flush()
        
        for db_obj in db_objs:
            await db.refresh(db_obj)
        
        logger.info(f"Created {len(db_objs)} {self.model.__name__} records")
        return db_objs
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        exclude_unset: bool = True
    ) -> ModelType:
        """Update a record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=exclude_unset)
        
        # Update object attributes
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        
        logger.info(f"Updated {self.model.__name__} with id {db_obj.id}")
        return db_obj
    
    async def update_by_id(
        self,
        db: AsyncSession,
        *,
        id: Union[str, UUID],
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> Optional[ModelType]:
        """Update a record by ID."""
        db_obj = await self.get(db, id)
        if not db_obj:
            return None
        return await self.update(db, db_obj=db_obj, obj_in=obj_in)
    
    async def delete(
        self,
        db: AsyncSession,
        *,
        id: Union[str, UUID],
         
        soft: bool = True
    ) -> Optional[ModelType]:
        """Delete a record (soft or hard delete)."""
        db_obj = await self.get(db, id, include_deleted=True)
        
        if not db_obj:
            return None
        
        if soft and hasattr(self.model, 'deleted_at'):
            # Soft delete
            from datetime import datetime
            db_obj.deleted_at = datetime.utcnow()
            db.add(db_obj)
            logger.info(f"Soft deleted {self.model.__name__} with id {id}")
        else:
            # Hard delete
            await db.delete(db_obj)
            logger.info(f"Hard deleted {self.model.__name__} with id {id}")
        
        await db.flush()
        return db_obj
    
    async def restore(
        self,
        db: AsyncSession,
        *,
        id: Union[str, UUID],
    ) -> Optional[ModelType]:
        """Restore a soft-deleted record."""
        db_obj = await self.get(db, id, include_deleted=True)
        
        if not db_obj or not hasattr(db_obj, 'deleted_at'):
            return None
        
        db_obj.deleted_at = None
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        
        logger.info(f"Restored {self.model.__name__} with id {id}")
        return db_obj
    
    async def exists(
        self,
        db: AsyncSession,
        *,
        id: Union[str, UUID],
    ) -> bool:
        """Check if a record exists."""
        query = select(self.model.id).where(self.model.id == id)
        query = self._apply_soft_delete_filter(query, include_deleted=False)
        
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_by_field(
        self,
        db: AsyncSession,
        *,
        field: str,
        value: Any,
         
        include_deleted: bool = False,
        include_inactive: bool = False
    ) -> Optional[ModelType]:
        """Get a record by a specific field value."""
        if not hasattr(self.model, field):
            raise ValueError(f"Model {self.model.__name__} does not have field {field}")
        
        query = select(self.model).where(getattr(self.model, field) == value)
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_is_active_filter(query, include_inactive)

        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_fields(
        self,
        db: AsyncSession,
        *,
        fields: Dict[str, Any],
         
        include_deleted: bool = False,
        include_inactive: bool = False
    ) -> List[ModelType]:
        """Get records matching multiple field values."""
        query = select(self.model)
        
        for field, value in fields.items():
            if not hasattr(self.model, field):
                raise ValueError(f"Model {self.model.__name__} does not have field {field}")
            query = query.where(getattr(self.model, field) == value)
        
        query = self._apply_soft_delete_filter(query, include_deleted)
        query = self._apply_is_active_filter(query, include_inactive)

        result = await db.execute(query)
        return result.scalars().all()

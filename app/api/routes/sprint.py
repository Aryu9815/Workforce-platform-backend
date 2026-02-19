"""
Task management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.api.schemas import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse
)
from app.schemas.sprint_schemas import (
    SprintCreate,
    SprintEnd,
    SprintResponse,
    SprintUpdate
)
from app.models.tenant import  Sprint
from app.db.base import get_db_session
from app.services.crud import CRUDService
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger
from app.services.sprints import SprintService

logger = get_logger(__name__)
router = APIRouter(prefix="/sprints", tags=["Sprint Management"])

sprint_crud = CRUDService(Sprint)
sprint_service = SprintService()


@router.get("", response_model=PaginatedResponse)
async def list_sprints(
    request: Request,
    pagination: PaginationParams = Depends(),
    project_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all tasks with filtering."""
    
    filters = {}
    if project_id:
        filters["project_id"] = project_id
    
    total = await sprint_crud.count(db, filters=filters)
    
    sprints = await sprint_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    
    sprint_responses = []
    for sprint in sprints:
        sprint_responses.append(
            SprintResponse(
                id=sprint.id,
                project_id=sprint.project_id,
                name=sprint.name,
                goal=sprint.goal,
                status=sprint.status,
                capacity=sprint.capacity,
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                created_at=sprint.created_at,
                updated_at=sprint.updated_at,
                created_by=sprint.created_by,
                updated_by=sprint.updated_by
        ))
    
    return PaginatedResponse.create(
        items=sprint_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
async def create_sprint(
    request: Request,
    sprint_data: SprintCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new task."""
    user_id = getattr(request.state, 'user_id', None)
    
    sprint = await sprint_service.create_sprint(
        db,
        user_id=user_id,
        data=sprint_data
    )
     
    # Publish event
    await publish_event(
        event_type=EventType.SPRINT_CREATED,
        aggregate_type="sprint",
        aggregate_id=str(sprint.id),
        payload={
            "name": sprint.name,
            "project_id": str(sprint.project_id),
            "created_by": user_id
        }
    )
    
    logger.info(f"Task created: {sprint.id}")
    
    return SprintResponse(
        id=sprint.id,
        name=sprint.name,
        project_id=sprint.project_id,
        goal=sprint.goal,
        status=sprint.status,
        capacity=sprint.capacity,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        created_at=sprint.created_at,
        updated_at=sprint.updated_at,
        created_by=sprint.created_by,
        updated_by=sprint.updated_by
    )


@router.get("/{sprint_id}", response_model=SprintResponse)
async def get_task(
    request: Request,
    sprint_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific task by ID."""
    
    return await sprint_service.get_sprint(db, sprint_id)

@router.put("/{sprint_id}", response_model=SprintResponse)
async def update_sprint(
    request: Request,
    sprint_id: UUID,
    sprint_data: SprintUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a task."""
    user_id = getattr(request.state, 'user_id', None)
    
    updated_sprint = await sprint_service.update_sprint(
        db,
        sprint_id=sprint_id,
        user_id=user_id,
        data=sprint_data
    )
    
    # Publish event
    await publish_event(
        event_type=EventType.SPRINT_UPDATED,
        aggregate_type="sprint",
        aggregate_id=str(updated_sprint.id),
        payload={
            "name": updated_sprint.name,
            "updated_by": user_id
        }
    )
    
    logger.info(f"Task updated: {updated_sprint.id}")
    
    return SprintResponse(
        id=updated_sprint.id,
        project_id=updated_sprint.project_id,
        name=updated_sprint.name,
        goal=updated_sprint.goal,
        status=updated_sprint.status,
        capacity=updated_sprint.capacity,
        start_date=updated_sprint.start_date,
        end_date=updated_sprint.end_date,
        created_at=updated_sprint.created_at,
        updated_at=updated_sprint.updated_at,
        created_by=updated_sprint.created_by,
        updated_by=updated_sprint.updated_by
    )


@router.delete("/{sprint_id}", response_model=SuccessResponse)
async def delete_sprint(
    request: Request,
    sprint_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a task."""
    user_id = getattr(request.state, 'user_id', None)
    
    sprint = await sprint_service.delete_sprint(db, sprint_id, user_id)
    
    # Publish event
    await publish_event(
        event_type=EventType.SPRINT_DELETED,
        aggregate_type="sprint",
        aggregate_id=str(sprint_id),
        payload={
            "name": sprint.name,
            "deleted_by": user_id
        }
    )
    
    logger.info(f"Task deleted: {sprint_id}")
    
    return SuccessResponse(message="Task deleted successfully")

@router.post("/{sprint_id}/end", response_model=SprintResponse)
async def end_sprint(
    request: Request,   
    sprint_id: UUID,
    end_sprint_data: SprintEnd,
    db: AsyncSession = Depends(get_db_session)
):  
    user_id = getattr(request.state, 'user_id', None)
    sprint = await sprint_service.end_sprint(db, sprint_id, user_id, end_sprint_data)
    return SprintResponse(
        id=sprint.id,
        project_id=sprint.project_id,
        name=sprint.name,
        goal=sprint.goal,
        status=sprint.status,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        created_at=sprint.created_at,
        updated_at=sprint.updated_at,
        created_by=sprint.created_by,
        updated_by=sprint.updated_by
    )
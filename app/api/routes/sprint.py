from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.schemas import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    SprintCreate,
    SprintEnd,
    SprintResponse,
    SprintUpdate
)
from app.db.base import get_db_session
from app.services.crud import sprint_crud
from app.core.logging_config import get_logger
from app.services import sprint_service, notify
from app.utils.rbac_middleware import require_permissions

logger = get_logger(__name__)
router = APIRouter(prefix="/sprints", tags=["Sprint Management"])



@router.get("", response_model=PaginatedResponse)
@require_permissions(["sprint:view"])
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
                sprint_number=sprint.sprint_number,
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
@require_permissions(["sprint:create"])
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
@require_permissions(["task:view"])
async def get_task(
    request: Request,
    sprint_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific task by ID."""
    
    return await sprint_service.get_sprint(db, sprint_id)

@router.put("/{sprint_id}", response_model=SprintResponse)
@require_permissions(["sprint:update"])
async def update_sprint(
    request: Request,
    sprint_id: UUID,
    sprint_data: SprintUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a task."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    updated_sprint = await sprint_service.update_sprint(
        db,
        sprint_id=sprint_id,
        user_id=user_id,
        data=sprint_data
    )
    
    _ = await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': f"Sprint updated: {updated_sprint.sprint_number}",
            'message': f"You have updated the sprint {updated_sprint.sprint_number} named {updated_sprint.name}"
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
@require_permissions(["sprint:delete"])
async def delete_sprint(
    request: Request,
    sprint_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a task."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    sprint = await sprint_service.delete_sprint(db, sprint_id, user_id)
    _ = await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': f"Sprint deleted: {sprint.sprint_number}",
            'message': f"You have deleted the sprint {sprint.sprint_number} named {sprint.name}"
        }
    )
    logger.info(f"Task deleted: {sprint_id}")
    
    return SuccessResponse(message="Task deleted successfully")

@router.post("/{sprint_id}/end", response_model=SprintResponse)
@require_permissions(["sprint:complete"])
async def end_sprint(
    request: Request,   
    sprint_id: UUID,
    end_sprint_data: SprintEnd,
    db: AsyncSession = Depends(get_db_session)
):  
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    sprint = await sprint_service.end_sprint(db, sprint_id, user_id, end_sprint_data)
    
    await notify.notify_end_sprint(db, sprint, tenant_id, user_id)
    
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
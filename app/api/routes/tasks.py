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
from app.schemas.task_schemas import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    CommentCreate,
    CommentResponse,
    CommentUpdate
)
from app.models.tenant import Task, TaskAssignee
from app.db.base import get_db_session
from app.services.crud import CRUDService
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger
from app.services.task import TaskService
from app.utils.rbac_middleware import require_permissions
logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["Task Management"])

task_crud = CRUDService(Task)
task_assignee_crud = CRUDService(TaskAssignee)
task_service = TaskService()



@router.get("", response_model=PaginatedResponse)
@require_permissions(["task:view"])
async def list_tasks(
    request: Request,
    pagination: PaginationParams = Depends(),
    project_id: Optional[UUID] = None,
    status_id: Optional[UUID] = None,
    priority: Optional[str] = None,
    sprint_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all tasks with filtering."""
    
    filters = {}
    if project_id:
        filters["project_id"] = project_id
    if status_id:
        filters["status_id"] = status_id
    if priority:
        filters["priority"] = priority
    filters["sprint_id"] = sprint_id
    
    total = await task_crud.count(db, filters=filters)
    
    tasks = await task_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    
    task_responses = []
    for task in tasks:
        task_responses.append(TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            task_type=task.task_type,
            estimated_hours=task.estimated_hours,
            estimated_cost=task.estimated_cost,
            start_date=task.start_date,
            due_date=task.due_date,
            project_id=task.project_id,
            parent_task_id=task.parent_task_id,
            workflow_state_id=task.workflow_state_id,
            status_name=None,
            status_color=None,
            actual_hours=task.actual_hours,
            actual_cost=task.actual_cost,
            completed_at=task.completed_at,
            created_by=task.created_by,
            progress_percentage=task.progress_percentage,
            milestone=task.milestone,
            billable=task.billable,
            created_at=task.created_at,
            updated_at=task.updated_at,
            assignees=[]
        ))
    
    return PaginatedResponse.create(
        items=task_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.get("/{proejct_id}/backlogs", response_model=PaginatedResponse)
@require_permissions(["task:view"])
async def list_backlog_tasks(
    request: Request,
    pagination: PaginationParams = Depends(),
    project_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all tasks with filtering."""
    
    filters = {}
    if project_id:
        filters["project_id"] = project_id
    filters["sprint_id"] = None
    
    total = await task_crud.count(db, filters=filters)
    
    tasks = await task_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    
    task_responses = []
    for task in tasks:
        task_responses.append(TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            task_type=task.task_type,
            estimated_hours=task.estimated_hours,
            estimated_cost=task.estimated_cost,
            start_date=task.start_date,
            due_date=task.due_date,
            project_id=task.project_id,
            parent_task_id=task.parent_task_id,
            workflow_state_id=task.workflow_state_id,
            status_name=None,
            status_color=None,
            actual_hours=task.actual_hours,
            actual_cost=task.actual_cost,
            completed_at=task.completed_at,
            created_by=task.created_by,
            progress_percentage=task.progress_percentage,
            milestone=task.milestone,
            billable=task.billable,
            created_at=task.created_at,
            updated_at=task.updated_at,
            assignees=[]
        ))
    
    return PaginatedResponse.create(
        items=task_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(["task:create"])
async def create_task(
    request: Request,
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new task."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    task = await task_service.create_task(
        db,
        user_id=user_id,
        data=task_data
    )
     
    # Publish event
    await publish_event(
        event_type=EventType.TASK_CREATED,
        aggregate_type="task",
        aggregate_id=str(task.id),
        payload={
            "title": task.title,
            "project_id": str(task.project_id),
            "created_by": user_id
        }
    )
    
    logger.info(f"Task created: {task.id}")
    
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        task_type=task.task_type,
        estimated_hours=task.estimated_hours,
        estimated_cost=task.estimated_cost,
        start_date=task.start_date,
        due_date=task.due_date,
        project_id=task.project_id,
        parent_task_id=task.parent_task_id,
        status_id=task.workflow_state_id,
        actual_hours=task.actual_hours,
        actual_cost=task.actual_cost,
        completed_at=task.completed_at,
        created_by=task.created_by,
        progress_percentage=task.progress_percentage,
        milestone=task.milestone,
        billable=task.billable,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.get("/{task_id}", response_model=TaskResponse)
@require_permissions(["task:view"])
async def get_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific task by ID."""
    
    return await task_service.get_task(db, task_id)


@router.put("/{task_id}", response_model=TaskResponse)
@require_permissions(["task:update"])
async def update_task(
    request: Request,
    task_id: UUID,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a task."""
    user_id = getattr(request.state, 'user_id', None)
    
    updated_task = await task_service.update_task(
        db,
        task_id=task_id,
        user_id=user_id,
        data=task_data
    )
    
    # Publish event
    await publish_event(
        event_type=EventType.TASK_UPDATED,
        aggregate_type="task",
        aggregate_id=str(updated_task.id),
        payload={
            "title": updated_task.title,
            "progress": updated_task.progress_percentage,
            "updated_by": user_id
        }
    )
    
    logger.info(f"Task updated: {updated_task.id}")
    
    return TaskResponse(
        id=updated_task.id,
        title=updated_task.title,
        description=updated_task.description,
        priority=updated_task.priority,
        task_type=updated_task.task_type,
        estimated_hours=updated_task.estimated_hours,
        estimated_cost=updated_task.estimated_cost,
        start_date=updated_task.start_date,
        due_date=updated_task.due_date,
        project_id=updated_task.project_id,
        parent_task_id=updated_task.parent_task_id,
        workflow_state_id=updated_task.workflow_state_id,
        actual_hours=updated_task.actual_hours,
        actual_cost=updated_task.actual_cost,
        completed_at=updated_task.completed_at,
        created_by=updated_task.created_by,
        progress_percentage=updated_task.progress_percentage,
        milestone=updated_task.milestone,
        billable=updated_task.billable,
        created_at=updated_task.created_at,
        updated_at=updated_task.updated_at
    )


@router.delete("/{task_id}", response_model=SuccessResponse)
@require_permissions(["task:delete"])
async def delete_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a task."""
    user_id = getattr(request.state, 'user_id', None)
    
    task = await task_service.delete_task(db, task_id, user_id)
    
    # Publish event
    await publish_event(
        event_type=EventType.TASK_DELETED,
        aggregate_type="task",
        aggregate_id=str(task_id),
        payload={
            "title": task.title,
            "deleted_by": user_id
        }
    )
    
    logger.info(f"Task deleted: {task_id}")
    
    return SuccessResponse(message="Task deleted successfully")


@router.post("/{task_id}/comments", response_model=CommentResponse)
@require_permissions(["task:comment"])
async def add_comment(
    request: Request,
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db_session)
):
    
    """Add a comment to a task."""  
    user_id = getattr(request.state, 'user_id', None)
    
    comment = await task_service.add_task_comment(
        db,
        data=comment_data,
        user_id=user_id
    )

    return CommentResponse(
        id=comment.id,
        task_id=comment.task_id,
        user_id=comment.user_id,
        content=comment.content,
        is_internal=comment.is_internal,
        parent_comment_id=comment.parent_comment_id,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        created_by=comment.created_by,
        updated_by=comment.updated_by
    )


@router.get("/{task_id}/comments", response_model=List[CommentResponse])
@require_permissions(["task:view"])
async def get_comments(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get all comments for a task."""
    return await task_service.get_comments(db, task_id)

@router.delete("/{task_id}/comments/{comment_id}", response_model=SuccessResponse)
@require_permissions(["task:comment"])
async def delete_comment(
    request: Request,
    comment_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a comment."""
    user_id = getattr(request.state, 'user_id', None)
    
    await task_service.delete_comment(db, comment_id, user_id)
    
    return SuccessResponse(message="Comment deleted successfully")


@router.put("/{task_id}/comments/{comment_id}", response_model=CommentResponse)
@require_permissions(["task:comment"])
async def update_comment(
    request: Request,
    comment_id: UUID,
    comment_data: CommentUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, 'user_id', None)
    
    return await task_service.update_comment(db, comment_id, user_id, comment_data)
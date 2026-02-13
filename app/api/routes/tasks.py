"""
Task management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.api.schemas import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse
)
from app.schemas.task_schemas import (
    TaskCreate,
    TaskResponse,
    TaskUpdate
)
from app.models.tenant import Task, TaskAssignee
from app.db.base import get_db_session
from app.services.crud import CRUDService
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger
from app.services.task import TaskService

logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["Task Management"])

task_crud = CRUDService(Task)
task_assignee_crud = CRUDService(TaskAssignee)
task_service = TaskService()



@router.get("", response_model=PaginatedResponse)
async def list_tasks(
    request: Request,
    pagination: PaginationParams = Depends(),
    project_id: Optional[UUID] = None,
    status_id: Optional[UUID] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all tasks with filtering."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    filters = {}
    if project_id:
        filters["project_id"] = project_id
    if status_id:
        filters["status_id"] = status_id
    if priority:
        filters["priority"] = priority
    
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
            status_id=task.workflow_state_id,
            status_name=None,  # TODO: Fetch status name
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
            assignees=[]  # TODO: Fetch assignees
        ))
    
    return PaginatedResponse.create(
        items=task_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
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
async def get_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific task by ID."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    task = await task_crud.get(db, task_id, tenant_id=tenant_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
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
        status_id=task.status_id,
        actual_hours=task.actual_hours,
        actual_cost=task.actual_cost,
        completed_at=task.completed_at,
        created_by=task.created_by,
        progress_percentage=task.progress_percentage,
        milestone=task.milestone,
        billable=task.billable,
        deleted_at=task.deleted_at,
        created_at=task.created_at,
        updated_at=task.updated_at
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    request: Request,
    task_id: UUID,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a task."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    task = await task_crud.get(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if task is being completed
    was_completed = task.progress_percentage < 100 and task_data.progress_percentage == 100
    
    update_data = task_data.model_dump(exclude_unset=True)
    
    if was_completed:
        update_data["completed_at"] = datetime.utcnow()
    
    updated_task = await task_crud.update(
        db,
        db_obj=task,
        obj_in=update_data
    )
    await db.commit()
    await db.refresh(updated_task)
    
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
    
    # Publish completion event
    if was_completed:
        await publish_event(
            event_type=EventType.TASK_COMPLETED,
            aggregate_type="task",
            aggregate_id=str(updated_task.id),
            tenant_id=tenant_id,
            payload={
                "title": updated_task.title,
                "project_id": str(updated_task.project_id),
                "actual_hours": updated_task.actual_hours,
                "completed_by": user_id
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
        status_id=updated_task.workflow_state_id,
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
async def delete_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a task."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    task = await task_crud.delete(
        db,
        id=task_id,
        tenant_id=tenant_id,
        soft=True
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Publish event
    await publish_event(
        event_type=EventType.TASK_DELETED,
        aggregate_type="task",
        aggregate_id=str(task_id),
        tenant_id=tenant_id,
        payload={
            "title": task.title,
            "deleted_by": user_id
        }
    )
    
    logger.info(f"Task deleted: {task_id}")
    
    return SuccessResponse(message="Task deleted successfully")


@router.post("/{task_id}/assign", response_model=SuccessResponse)
async def assign_task(
    request: Request,
    task_id: UUID,
    assignee_ids: List[UUID],
    db: AsyncSession = Depends(get_db_session)
):
    """Assign task to staff members."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    task = await task_crud.get(db, task_id, tenant_id=tenant_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Remove existing assignees
    existing = await task_assignee_crud.get_by_fields(
        db,
        fields={"task_id": task_id},
        tenant_id=tenant_id
    )
    for assignee in existing:
        await db.delete(assignee)
    
    # Add new assignees
    for i, assignee_id in enumerate(assignee_ids):
        await task_assignee_crud.create(
            db,
            obj_in={
                "task_id": task_id,
                "staff_id": assignee_id,
                "assigned_by": user_id,
                "is_primary": i == 0
            },
            tenant_id=tenant_id
        )
    
    # Publish events
    for assignee_id in assignee_ids:
        await publish_event(
            event_type=EventType.TASK_ASSIGNED,
            aggregate_type="task",
            aggregate_id=str(task_id),
            tenant_id=tenant_id,
            payload={
                "title": task.title,
                "assignee_id": str(assignee_id),
                "assigned_by": user_id
            }
        )
    
    logger.info(f"Task {task_id} assigned to {len(assignee_ids)} users")
    
    return SuccessResponse(message="Task assigned successfully")

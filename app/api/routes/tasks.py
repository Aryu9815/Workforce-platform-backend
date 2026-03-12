from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.models.tenant.task import Task
from app.schemas import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    CommentCreate,
    CommentResponse,
    CommentUpdate
)
from sqlalchemy import select
from app.db.base import get_db_session
from app.services.crud import task_crud
from app.core.logging_config import get_logger
from app.services import task_service, notify
from app.utils.rbac_middleware import require_permissions

logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["Task Management"])


from app.models.tenant.task import TaskLabel
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
    result = await db.execute(
            select(Task, TaskLabel)
            .outerjoin(TaskLabel, TaskLabel.id == Task.task_label_id)
            .where(Task.is_deleted == False)
            .offset(pagination.skip)
            .limit(pagination.limit)
        )

    rows = result.all()
    
    task_responses = []
    for task , label  in rows:
        task_responses.append(TaskResponse(
            id=task.id,
            task_label_id=task.task_label_id,
            task_label={
                "id": label.id,
                "label": label.label,
                "description": label.description,
                "color": label.color
            } if label else None,

            title=task.title,
            description=task.description,
            priority=task.priority,
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
            assignees=[],
            ticket=f"{task.ticket_code}-{task.ticket_number}" if task.ticket_code and task.ticket_number else None,
            ticket_code=task.ticket_code,
            ticket_number=task.ticket_number
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
    
    task_responses = await task_service.get_backlogs(db, project_id)
    
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
    print("create task",user_id)
    task, assignee = await task_service.create_task(
        db,
        user_id=user_id,
        data=task_data
    )
    logger.info(f"Task created: {task.id}")
    await notify.notify_task_assignment(db, task, assignee, tenant_id, user_id)
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
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


@router.get("/assigned/{staff_id}", response_model=List[TaskResponse])
@require_permissions(["task:view"])
async def get_assigned_tasks(
    request: Request,
    staff_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific task by ID."""
    
    return await task_service.get_assigned_tasks_for_staff(db, staff_id)

@router.get("/{task_id}", response_model=TaskResponse)
@require_permissions(["task:view"])
async def get_task(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific task by ID."""
    task  = await task_service.get_task(db, task_id)
    return task
    

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
    
    logger.info(f"Task updated: {updated_task.id}")
    
    return TaskResponse(
        id=updated_task.id,
        title=updated_task.title,
    
        description=updated_task.description,
        priority=updated_task.priority,
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
    
    await task_service.delete_task(db, task_id, user_id)
    
    logger.info(f"Task deleted: {task_id}")
    
    return SuccessResponse(message="Task deleted successfully")


@router.post("/{task_id}/comments", response_model=CommentResponse)
@require_permissions(["comment:create"])
async def add_comment(
    request: Request,
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db_session)
):
    
    """Add a comment to a task."""  
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    comment, task = await task_service.add_task_comment(
        db,
        data=comment_data,
        user_id=user_id
    )
    _ = await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': f"Comment - {task.ticket_code}-{task.ticket_number}",
            'message': comment.content
        }
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
@require_permissions(["comment:view"])
async def get_comments(
    request: Request,
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get all comments for a task."""
    return await task_service.get_comments(db, task_id)

@router.delete("/{task_id}/comments/{comment_id}", response_model=SuccessResponse)
@require_permissions(["comment:delete"])
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
@require_permissions(["comment:update"])
async def update_comment(
    request: Request,
    comment_id: UUID,
    comment_data: CommentUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    user_id = getattr(request.state, 'user_id', None)
    
    return await task_service.update_comment(db, comment_id, user_id, comment_data)

@router.get("/{sprint_id}/get_tickets")
@require_permissions(["task:create"])
async def get_tickets(
    request: Request,
    sprint_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    return await task_service.get_ticket(db, sprint_id)

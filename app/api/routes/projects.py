"""
Project management API routes.
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
from app.schemas.project_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse
)
from app.models.tenant import Project
from app.db.base import get_db_session
from app.schemas.project_schemas import ProjectMemberResponse, CreateProjectMember
from app.services.crud import CRUDService
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger
from app.services.projects import ProjectService
from app.services.team import TeamService

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["Project Management"])

project_crud = CRUDService(Project)
project_service = ProjectService()
team_service = TeamService()




@router.get("", response_model=PaginatedResponse)
async def list_projects(
    request: Request,
    pagination: PaginationParams = Depends(),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all projects with filtering."""
    
    filters = {}
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    
    total = await project_crud.count(db, filters=filters)
    
    projects = await project_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    
    project_responses = []
    for project in projects:
        project_responses.append(ProjectResponse(
            id=project.id,
            name=project.name,
            code=project.code,
            description=project.description,
            status=project.status,
            priority=project.priority,
            project_type=project.project_type,
            start_date=project.start_date,
            end_date=project.end_date,
            budget=project.budget,
            currency=project.currency,
            parent_project_id=project.parent_project_id,
            client_id=project.client_id,
            project_manager_id=project.project_manager_id,
            actual_start_date=project.actual_start_date,
            actual_end_date=project.actual_end_date,
            cost_estimate=project.cost_estimate,
            actual_cost=project.actual_cost,
            progress_percentage=project.progress_percentage,
            is_template=project.is_template,
            created_at=project.created_at,
            updated_at=project.updated_at,
            manager_name=None 
        ))
    
    return PaginatedResponse.create(
        items=project_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new project."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    print('creating project')
    project = await project_service.create_project(
        db,
        data=project_data,
        user_id=user_id
    )
    
    # Publish event
    await publish_event(
        event_type=EventType.PROJECT_CREATED,
        aggregate_type="project",
        aggregate_id=str(project.id),
        payload={
            "name": project.name,
            "code": project.code,
            "project_manager_id": str(project.project_manager_id),
            "created_by": user_id
        }
    )
    
    logger.info(f"Project created: {project.id}")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        status=project.status,
        priority=project.priority,
        project_type=project.project_type,
        start_date=project.start_date,
        end_date=project.end_date,
        budget=project.budget,
        currency=project.currency,
        parent_project_id=project.parent_project_id,
        client_id=project.client_id,
        project_manager_id=project.project_manager_id,
        actual_start_date=project.actual_start_date,
        actual_end_date=project.actual_end_date,
        cost_estimate=project.cost_estimate,
        actual_cost=project.actual_cost,
        progress_percentage=project.progress_percentage,
        is_template=project.is_template,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.post("", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_project_member(
    request: Request,
    project_data: CreateProjectMember,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new project."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    member = await team_service.add_member(
        db,
        data=project_data,
        tenant_id=tenant_id
    )
    
    logger.info(f"Member added to Project: {member.id}")
    
    return ProjectMemberResponse(
        id=member.id,
        staff_id=member.staff_id,
        project_id=member.project_id,
        role=member.role,
        joined_at=member.joined_at,
        left_at=member.left_at,
        created_at=member.created_at,
        updated_at=member.updated_at
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific project by ID."""
    return await project_service.get_project(db, project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: Request,
    project_id: UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a project."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    project = await project_crud.get(db, project_id, tenant_id=tenant_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Track if status changed to completed
    was_completed = project.status != "completed" and project_data.status == "completed"
    
    updated_project = await project_crud.update(
        db,
        db_obj=project,
        obj_in=project_data.model_dump(exclude_unset=True)
    )
    
    # Publish event
    await publish_event(
        event_type=EventType.PROJECT_UPDATED,
        aggregate_type="project",
        aggregate_id=str(updated_project.id),
        tenant_id=tenant_id,
        payload={
            "name": updated_project.name,
            "status": updated_project.status,
            "progress": updated_project.progress_percentage,
            "updated_by": user_id
        }
    )
    
    logger.info(f"Project updated: {updated_project.id}")
    
    return ProjectResponse(
        id=updated_project.id,
        name=updated_project.name,
        code=updated_project.code,
        description=updated_project.description,
        status=updated_project.status,
        priority=updated_project.priority,
        project_type=updated_project.project_type,
        start_date=updated_project.start_date,
        end_date=updated_project.end_date,
        budget=updated_project.budget,
        currency=updated_project.currency,
        parent_project_id=updated_project.parent_project_id,
        client_id=updated_project.client_id,
        project_manager_id=updated_project.project_manager_id,
        actual_start_date=updated_project.actual_start_date,
        actual_end_date=updated_project.actual_end_date,
        cost_estimate=updated_project.cost_estimate,
        actual_cost=updated_project.actual_cost,
        progress_percentage=updated_project.progress_percentage,
        is_template=updated_project.is_template,
        deleted_at=updated_project.deleted_at,
        created_at=updated_project.created_at,
        updated_at=updated_project.updated_at
    )


@router.delete("/{project_id}", response_model=SuccessResponse)
async def delete_project(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a project."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    project = await project_crud.delete(
        db,
        id=project_id,
        tenant_id=tenant_id,
        soft=True
    )
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Publish event
    await publish_event(
        event_type=EventType.PROJECT_DELETED,
        aggregate_type="project",
        aggregate_id=str(project_id),
        tenant_id=tenant_id,
        payload={
            "name": project.name,
            "deleted_by": user_id
        }
    )
    
    logger.info(f"Project deleted: {project_id}")
    
    return SuccessResponse(message="Project deleted successfully")


@router.get("/{project_id}/stats")
async def get_project_stats(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get project statistics."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    project = await project_crud.get(db, project_id, tenant_id=tenant_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # TODO: Calculate actual statistics
    return {
        "project_id": str(project_id),
        "total_tasks": 0,
        "completed_tasks": 0,
        "in_progress_tasks": 0,
        "overdue_tasks": 0,
        "total_hours": 0,
        "budget_utilization": 0,
        "team_size": 0
    }

@router.get("/{project_id}/members")
async def get_project_members(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get project members."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    members = await team_service.get_project_members(db, project_id)
    return members
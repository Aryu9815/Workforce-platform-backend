from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.schemas import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    UpdateProjectMember,
    ProjectMemberResponse, 
    CreateProjectMember
)
from app.db.base import get_db_session
from app.core.logging_config import get_logger
from app.services import project_service, team_service, notify
from app.utils.rbac_middleware import require_permissions
from app.services.crud import staff_crud, project_crud

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["Project Management"])


@router.get("", response_model=PaginatedResponse)
@require_permissions(["project:view"])
async def list_projects(
    request: Request,
    pagination: PaginationParams = Depends(),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all projects with filtering."""
    
    project_responses, total = await project_service.get_project_list(
        db,
        pagination=pagination,
        status=status,
        priority=priority,
        search=search
    )
    return PaginatedResponse.create(
        items=project_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(["project:create"])
async def create_project(
    request: Request,
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new project."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    project = await project_service.create_project(
        db,
        data=project_data,
        user_id=user_id
    )
    staff = await staff_crud.get(db, project.project_manager_id)
    _ = await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(user_id),
            'title': f"New project {project.name}",
            'message': f"You have created a new project named {project.name}.",
            }
        )
    
    _ = await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(staff.user_id),
            'title': f"New project {project.name}",
            'message': f"You are assigned to a new project named {project.name} as a project manager.",
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


@router.post("/member", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(["project:manage-members"])
async def add_project_member(
    request: Request,
    project_data: CreateProjectMember,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new project."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    member = await team_service.add_member(
        db,
        data=project_data,
        user_id=user_id
    )
    
    logger.info(f"Member added to Project: {member.id}")
    await notify.notify_project_member(db, member, tenant_id, user_id)
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
@require_permissions(["project:view"])
async def get_project(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific project by ID."""
    return await project_service.get_project(db, project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
@require_permissions(["project:update"])
async def update_project(
    request: Request,
    project_id: UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a project."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    updated_project = await project_service.update_project(db, project_id, user_id, project_data)
    
    _ = await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(user_id),
            'title': f"Project updated: {updated_project.name}",
            'message': f"You have updated the project named {updated_project.name}.",
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
        created_at=updated_project.created_at,
        updated_at=updated_project.updated_at
    )


@router.delete("/{project_id}", response_model=SuccessResponse)
@require_permissions(["project:delete"])
async def delete_project(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a project."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    project = await project_service.delete_project(db, project_id, user_id)
    _ = await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(user_id),
            'title': f"Project deleted: {project.name}",
            'message': f"You have deleted the project named {project.name}.",
            }
        )
    logger.info(f"Project deleted: {project_id}")
    
    return SuccessResponse(message="Project deleted successfully")

@router.get("/{project_id}/members")
@require_permissions(["project:view-members"])
async def get_project_members(
    request: Request,
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get project members."""
    members = await team_service.get_project_members(db, project_id)
    return members

@router.delete("/member/{member_id}")
@require_permissions(["project:manage-members"])
async def remove_project_member(
    request: Request,
    member_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    member = await team_service.remove_member(db, member_id, user_id)

    await notify.notify_project_member(db, member, tenant_id, user_id, is_removed=True)
    
    return SuccessResponse(message="Member removed successfully")

@router.put("/member/{member_id}", response_model=ProjectMemberResponse)
@require_permissions(["project:manage-members"])
async def update_project_member(
    request: Request,
    member_id: UUID,
    data: UpdateProjectMember,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    member = await team_service.update_member(db, member_id, data, user_id) 
    project = await project_crud.get(db, member.project_id)
    staff = await staff_crud.get(db, member.staff_id)
    staff_by = await staff_crud.get_by_field(db, field="user_id", value=user_id)
    _ = await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(user_id),
            'title': f"Project member updated in project {project.name}",
            'message': f"You have updated {staff.first_name} {staff.last_name}'s role to {member.role} in project {project.name}."
            }
        )
    
    _ = await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(staff.user_id),
            'title': f"Project member updated in project {project.name}",
            'message': f"Your role has been updated to {member.role} in project {project.name} by {staff_by.first_name} {staff_by.last_name}"
            }
        )
    return member


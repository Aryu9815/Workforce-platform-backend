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
    ProjectResponse,
    UpdateProjectMember
)
from app.models.tenant import Project
from app.db.base import get_db_session
from app.schemas.workflow_schemas import (
    WorkflowResponse, 
    WorkflowStateResponse, 
    WorkflowUpdate,
    CreateWorkFlowState,
    UpdateWorkFlowState,
    CreateWorkflowTransition,
    UpdateWorkflowTransition,
    WorkflowTransitionResponse
    )
from app.services.crud import CRUDService
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger
from app.services.projects import ProjectService
from app.services.team import TeamService
from app.services.workflow import WorkflowService

logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["Workflows Management"])

project_crud = CRUDService(Project)
project_service = ProjectService()
team_service = TeamService()
workflow_service = WorkflowService()

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    request: Request,
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific project by ID."""
    data = await workflow_service.get_workflow(db, workflow_id)
    workflow = data['workflow']
    workflow_states = data['workflow_states']
    
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        is_default=workflow.is_default,
        is_system=workflow.is_system,
        entity_type=workflow.entity_type,
        workflow_states=workflow_states,
        settings=workflow.settings,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at
    )



@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: Request,
    project_id: UUID,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a project."""
    user_id = getattr(request.state, 'user_id', None)
    
    updated_project = await project_service.update_project(db, project_id, user_id, project_data)
    
    # Publish event
    await publish_event(
        event_type=EventType.PROJECT_UPDATED,
        aggregate_type="project",
        aggregate_id=str(updated_project.id),
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
        created_at=updated_project.created_at,
        updated_at=updated_project.updated_at
    )

@router.get("/{workflow_id}/states")
async def get_workflow_states(
    request: Request,
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get project members."""
    
    states = await workflow_service.get_workflow_states(db, workflow_id)
    return states

@router.get("/{workflow_id}/transitions", response_model=List[WorkflowTransitionResponse])
async def get_workflow_states(
    request: Request,
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get project members."""
    transitions = await workflow_service.get_workflow_transitions(db, workflow_id)
    return transitions


@router.delete("/{workflow_id}/states/{state_id}")
async def delete_state(
    request: Request,
    state_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    await workflow_service.delete_workflow_state(db, state_id, user_id)
    return SuccessResponse(message="state deleted successfully")


@router.delete("/{workflow_id}/transitions/{transition_id}")
async def delete_transition(
    request: Request,
    transition_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    await workflow_service.delete_workflow_transition(db, transition_id, user_id)
    return SuccessResponse(message="transition deleted successfully")

@router.put("/{workflow_id}/states/{state_id}")
async def update_state(
    request: Request,
    member_id: UUID,
    data: UpdateWorkFlowState,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    return await workflow_service.update_workflow_state(db, member_id, data, user_id) 

@router.put("/{workflow_id}/transitions/{transition_id}")
async def update_transition(
    request: Request,
    transition_id: UUID,
    data: UpdateWorkflowTransition,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    return await workflow_service.update_workflow_transition(db, transition_id, data, user_id) 

@router.post("/{workflow_id}/transitions")
async def create_transition(
    request: Request,
    data: CreateWorkflowTransition,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    return await workflow_service.add_workflow_transition(db, data, user_id)

@router.post("/{workflow_id}/states")
async def create_transition(
    request: Request,
    data: CreateWorkFlowState,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    return await workflow_service.add_workflow_state(db, data, user_id)



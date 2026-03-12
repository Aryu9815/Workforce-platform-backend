from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.db.base import get_db_session
from app.schemas import (
    WorkflowResponse, 
    CreateWorkFlowState,
    UpdateWorkFlowState,
    CreateWorkflowTransition,
    UpdateWorkflowTransition,
    WorkflowTransitionResponse,
    SuccessResponse
)
from app.core.logging_config import get_logger
from app.services import workflow_service, notify
from app.utils.rbac_middleware import require_permissions

logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["Workflows Management"])

@router.get("/{workflow_id}", response_model=WorkflowResponse)
@require_permissions(["project:view"])
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

@router.get("/{workflow_id}/states")
@require_permissions(["project:view"])
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
@require_permissions(["project:update"])
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
@require_permissions(["project:update"])
async def delete_transition(
    request: Request,
    transition_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    transition = await workflow_service.delete_workflow_transition(db, transition_id, user_id)
    await notify.notify_transition(db, transition, tenant_id, user_id, is_deleted=True)
    return SuccessResponse(message="transition deleted successfully")

@router.put("/{workflow_id}/states/{state_id}")
@require_permissions(["project:update"])
async def update_state(
    request: Request,
    state_id: UUID,
    data: UpdateWorkFlowState,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    return await workflow_service.update_workflow_state(db, state_id, data, user_id) 

@router.put("/{workflow_id}/transitions/{transition_id}")
@require_permissions(["project:update"])
async def update_transition(
    request: Request,
    transition_id: UUID,
    data: UpdateWorkflowTransition,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    transition =  await workflow_service.update_workflow_transition(db, transition_id, data, user_id) 
    await notify.notify_transition(db, transition, tenant_id, user_id)
    return transition

@router.post("/{workflow_id}/transitions")
@require_permissions(["project:update"])
async def create_transition(
    request: Request,
    data: CreateWorkflowTransition,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    transition = await workflow_service.add_workflow_transition(db, data, user_id) 
    await notify.notify_transition(db, transition, tenant_id, user_id)
    return transition

@router.post("/{workflow_id}/states")
@require_permissions(["project:update"])
async def create_state(
    request: Request,
    data: CreateWorkFlowState,
    db: AsyncSession = Depends(get_db_session)
):
    """Remove a project member."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    state = await workflow_service.add_workflow_state(db, data, user_id)
    await notify.notify_state(db, state, tenant_id, user_id)
    return state



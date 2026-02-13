from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from app.models.tenant import Workflow, WorkflowTransitions, Status, WorkflowState, TransitionsRules
from app.services.crud import CRUDService
from app.schemas.workflow_schemas import WorkflowCreate, WorkflowUpdate, WorkflowStateBase, CreateWorkFlowState, UpdateWorkFlowState, WorkflowTransitionBase, CreateWorkflowTransition, UpdateWorkflowTransition
from app.core.constants import DEFAULT_STATES, TRANSITION_MAP
from datetime import datetime, timezone
from fastapi import HTTPException, status


class WorkflowService:

    def __init__(self):
        self.workflow_crud = CRUDService(Workflow)
        self.workflow_transition_crud = CRUDService(WorkflowTransitions)
        self.status_crud = CRUDService(Status)
        self.workflow_state_crud = CRUDService(WorkflowState)
        self.transitions_rules_crud = CRUDService(TransitionsRules)

    async def create_default_workflow(self, db: AsyncSession, user_id: str):

        workflow = WorkflowCreate(
            name='Default Workflow',
            description='Default workflow for the project',
            is_default=True,
            is_system=True,
            entity_type='project',
            created_by=user_id
        )
        
        workflow = await self.workflow_crud.create(db, obj_in=workflow.model_dump())
        
        status_map = {}

        for name, category, is_initial, is_final, color, position in DEFAULT_STATES:
            state = CreateWorkFlowState(
                workflow_id=workflow.id,
                name=name,
                category=category,
                is_initial=is_initial,
                is_final=is_final,
                color=color,
                order_index=position,
                created_by=user_id
            )
            state = await self.workflow_state_crud.create(db, obj_in=state.model_dump())
            status_map[name] = state.id

        for from_s, to_s, requires_approval in TRANSITION_MAP:

            transition = CreateWorkflowTransition(
                workflow_id=workflow.id,
                from_state_id=status_map[from_s],
                to_state_id=status_map[to_s],
                requires_approval=requires_approval,
                name=f"{from_s} → {to_s}",
                description=f"Transition from {from_s} to {to_s}",
                auto_transition = False,
                created_by=user_id
            )
            await self.workflow_transition_crud.create(db, obj_in=transition.model_dump())    

        await db.commit()

        return workflow

    async def delete_workflow(self, db: AsyncSession, workflow_id: str, user_id: str):
        
        # delete workflow
        workflow = await self.workflow_crud.delete(db, id=workflow_id, user_id=user_id, soft=True) 
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        
        # delete workflow states
        states = await self.workflow_state_crud.delete_by_field(
            db, 
            field="workflow_id", 
            value=workflow_id, 
            user_id= user_id,
            soft=True
        )
        
        # delete state transitions
        transitions = await self.workflow_transition_crud.delete_by_field(
            db, 
            field="workflow_id", 
            value=workflow_id, 
            user_id= user_id,
            soft=True
        )
        
        # delete transition rules
        if transitions:
            for transition in transitions:
                await self.transitions_rules_crud.delete_by_field(
                    db, 
                    field="transition_id", 
                    value=transition.id, 
                    user_id= user_id,
                    soft=True
                )
        await db.commit()
        return workflow
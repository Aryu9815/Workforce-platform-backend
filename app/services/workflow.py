from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from app.models.tenant import Workflow, WorkflowTransitions, Status, WorkflowState, TransitionsRules
from app.services.crud import CRUDService
from app.schemas.workflow_schemas import WorkflowCreate, WorkflowUpdate, WorkflowStateBase, CreateWorkFlowState, UpdateWorkFlowState, WorkflowTransitionBase, CreateWorkflowTransition, UpdateWorkflowTransition, WorkflowTransitionResponse
from app.core.constants import DEFAULT_STATES, TRANSITION_MAP
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select


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

    async def get_workflow(self, db: AsyncSession, workflow_id: str):

        workflow = await self.workflow_crud.get(db, workflow_id)
        workflow_states = await self.workflow_state_crud.get_by_fields(
            db, fields={"workflow_id": workflow_id}
        )

        return {
            "workflow": workflow,
            "workflow_states": workflow_states
        }
    
    async def get_workflow_states(self, db: AsyncSession, workflow_id: str):
        workflow_states = await self.workflow_state_crud.get_by_fields(
            db, fields={"workflow_id": workflow_id}
        )
        return workflow_states

    async def add_workflow_state(self, db: AsyncSession, data: CreateWorkFlowState, user_id: str):
        """
        Create a new project, assign creator as manager,
        and auto-create a default workflow.
        """
        existed_state = await self.workflow_state_crud.get_by_fields(
            db,
            fields={
                "workflow_id": data.workflow_id,
                "name": data.name
            }
        )
        if existed_state:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="State already exists")
        data.created_by = user_id
        state = await self.workflow_state_crud.create(db, obj_in=data.model_dump())
        await db.commit()    
        return state
    
    async def update_workflow_state(self, db: AsyncSession, state_id: str, data: UpdateWorkFlowState, user_id: str):
        state = await self.workflow_state_crud.update_by_id(db, id=state_id, obj_in=data.model_dump(exclude_unset=True), updated_by=user_id)
        await db.commit()
        await db.refresh(state)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
        return state
    
    async def delete_workflow_state(self, db: AsyncSession, state_id: str, user_id: str):
        
        state = await self.workflow_state_crud.delete(
            db,
            id=state_id,
            user_id=user_id,
            soft=True
        )
        await db.commit()
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
        return state
    
    async def get_workflow_transitions(self, db: AsyncSession, workflow_id: str):
        transitions = await self.workflow_transition_crud.get_by_fields(
            db, fields={"workflow_id": workflow_id}
        )
        updated_transitions = []
        for transition in transitions:
            from_state = await self.workflow_state_crud.get(db, transition.from_state_id)
            to_state = await self.workflow_state_crud.get(db, transition.to_state_id)
            print(from_state.name, to_state.name)
            updated_transitions.append(
                WorkflowTransitionResponse(
                    id=transition.id,
                    workflow_id=transition.workflow_id,
                    from_state_id=transition.from_state_id,
                    to_state_id=transition.to_state_id,
                    from_state_name=from_state.name,
                    to_state_name=to_state.name,
                    name=transition.name,
                    description=transition.description,
                    request_approval=transition.request_approval,
                    approval_flow_id=transition.approval_flow_id,
                    auto_transition=transition.auto_transition,
                    condition_rules=transition.condition_rules,
                    created_at=transition.created_at,
                    updated_at=transition.updated_at
                )
            )
        return updated_transitions

    async def add_workflow_transition(self, db: AsyncSession, data: CreateWorkflowTransition, user_id: str):

        transition = await self.workflow_transition_crud.create(db, obj_in=data.model_dump(), user_id=user_id)
        await db.commit()
        return transition
    
    async def update_workflow_transition(self, db: AsyncSession, transition_id: str, data: UpdateWorkflowTransition, user_id: str):
        transition = await self.workflow_transition_crud.update_by_id(db, id=transition_id, obj_in=data.model_dump(exclude_unset=True), updated_by=user_id)
        await db.commit()
        await db.refresh(transition)
        if not transition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transition not found")
        return transition
    
    async def delete_workflow_transition(self, db: AsyncSession, transition_id: str, user_id: str):
        
        transition = await self.workflow_transition_crud.delete(
            db,
            id=transition_id,
            user_id=user_id,
            soft=True
        )
        await db.commit()
        if not transition:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transition not found")
        return transition
    
    async def verify_transition(self, db: AsyncSession, to_state_id: str, from_state_id: str):
        transitions = await self.workflow_transition_crud.get_by_fields(
            db, fields={"to_state_id": to_state_id, "from_state_id": from_state_id}
        )
        if not transitions:
            return False
        return True
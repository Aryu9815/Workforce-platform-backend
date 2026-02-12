from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from app.models.tenant import Workflow, WorkflowTransitions, Status, WorkflowState
from app.services.crud import CRUDService
from app.schemas.workflow_schemas import WorkflowCreate, WorkflowUpdate, WorkflowStates, CreateWorkFlowState, UpdateWorkFlowState, WorkflowTransitionBase, CreateWorkflowTransition, UpdateWorkflowTransition
from app.core.constants import DEFAULT_STATES, TRANSITION_MAP


class WorkflowService:

    def __init__(self):
        self.workflow_crud = CRUDService(Workflow)
        self.workflow_transition_crud = CRUDService(WorkflowTransitions)
        self.status_crud = CRUDService(Status)
        self.workflow_state_crud = CRUDService(WorkflowState)

    async def create_default_workflow(self, db: AsyncSession, project_id: str):

        workflow = WorkflowCreate(
            project_id=project_id,
            name='Default Workflow',
            description='Default workflow for the project',
            is_default=True,
            is_system=True,
            entity_type='project'
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
                position=position
            )
            state = await self.workflow_state_crud.create(db, obj_in=state.model_dump())
            status_map[name] = state


        for from_s, to_s, requires_approval in TRANSITION_MAP:
            transition = CreateWorkflowTransition(
                workflow_id=workflow.id,
                from_status_id=status_map[from_s].id,
                to_status_id=status_map[to_s].id,
                requires_approval=requires_approval,
                name=f"{from_s} → {to_s}",
                description=f"Transition from {from_s} to {to_s}",
                auto_transition = False
            )
            await self.workflow_transition_crud.create(db, obj_in=transition.model_dump())    

        await db.commit()

        return workflow

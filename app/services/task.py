from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from typing import List, Optional
from app.models.tenant import Task, TaskAssignee, TaskComment, TaskDependency, Project, WorkflowState, Workflow
from app.services.workflow import WorkflowService
from app.services.team import TeamService
from app.schemas.task_schemas import TaskCreate, TaskUpdate
from app.services.crud import CRUDService


class TaskService:

    def __init__(self):
        self.task_crud = CRUDService(Task)
        self.task_assignee_crud = CRUDService(TaskAssignee)

    async def create_task(
        self,
        db: AsyncSession,
        user_id: str,
        data: TaskCreate
    ):
        """
        Create a new project, assign creator as manager,
        and auto-create a default workflow.
        """
        project_id = data.project_id
        result = await db.execute(
            select(WorkflowState.id)
            .join(Workflow, WorkflowState.workflow_id == Workflow.id)
            .join(Project, Workflow.id == Project.workflow_id)
            .where(
                Project.id == project_id,
                WorkflowState.is_initial.is_(True),
                WorkflowState.is_active.is_(True),
                WorkflowState.is_deleted.is_(False),
            )
        )
        initial_state_id = result.scalar_one_or_none()
        if not initial_state_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Initial state not found'
            )
        task_data_dict = data.model_dump()
        task_data_dict["workflow_state_id"] = initial_state_id
        task_data_dict["created_by"] = user_id
        print('987',task_data_dict)
        task = await self.task_crud.create(
            db,
            obj_in=task_data_dict,
        )
        # for assignee_id in data.assignee_ids:
        #     await self.task_assignee_crud.create(
        #         db,
        #         obj_in={
        #             "task_id": task.id,
        #             "staff_id": assignee_id,
        #             "assigned_by": user_id,
        #             "is_primary": assignee_id == data.assignee_ids[0] if data.assignee_ids else False
        #         }
        #     )
        return task


    async def update_project(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str,
        data: dict
    ):
        """
        Update project details (allowed only for project managers).
        """
        project = await self.get_project(db, project_id)

        # Check permission
        if not await self.team_service.is_manager(db, project_id, user_id):
            raise Exception(status=403, detail="Only project managers can update the project")

        for key, value in data.items():
            setattr(project, key, value)

        await db.commit()
        await db.refresh(project)
        return project


    async def delete_project(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str
    ):
        """
        Soft-delete a project (manager only).
        """
        project = await self.get_project(db, project_id)

        if not await self.team_service.is_manager(db, project_id, user_id):
            raise Exception(status=403, detail="Only project managers can delete this project")

        project.is_archived = True

        await db.commit()
        return {"success": True}


    async def get_project(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Project:

        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise Exception(status=404, detail="Project not found")

        return project


    async def list_projects(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> List[Project]:

        result = await db.execute(
            select(Project).where(Project.tenant_id == tenant_id, Project.is_archived == False)
        )
        return result.scalars().all()

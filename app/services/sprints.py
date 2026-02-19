from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Sprint, Task, WorkflowState, Project
from app.schemas.sprint_schemas import SprintCreate, SprintEnd, SprintResponse, SprintUpdate
from app.services.crud import CRUDService
from app.services.task import TaskService 

class SprintService:

    def __init__(self):
        self.sprint_crud = CRUDService(Sprint)
        self.task_crud = CRUDService(Task)
        self.task_service = TaskService()
        self.workflow_state_crud = CRUDService(WorkflowState)
        self.project_crud = CRUDService(Project)


    async def create_sprint(
        self,
        db: AsyncSession,
        user_id: str,
        data: SprintCreate
    ):
        """
        Create a new project, assign creator as manager,
        and auto-create a default workflow.
        """
        sprint = await self.sprint_crud.create(
            db,
            obj_in=data.model_dump(),
            user_id=user_id
        )
        return sprint

    async def update_sprint(
        self,
        db: AsyncSession,
        sprint_id: str,
        user_id: str,
        data: SprintUpdate
    ):
        """
        Update project details (allowed only for project managers).
        """
        sprint = await self.sprint_crud.get(db, sprint_id)

        if not sprint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sprint not found"
            )
        updated_sprint = await self.sprint_crud.update(
            db,
            db_obj=sprint,
            updated_by=user_id,
            obj_in=data.model_dump(exclude_unset=True)
            )
        return updated_sprint


    async def delete_sprint(
        self,
        db: AsyncSession,
        sprint_id: str,
        user_id: str
    ):
        """
        Soft-delete a project (manager only).
        """
        sprint = await self.sprint_crud.get(db, sprint_id)
        if not sprint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sprint not found")
        tasks = await self.task_crud.get_by_fields(db, fields={"sprint_id": sprint_id})
        for task in tasks:
            await self.task_service.delete_task(db, task.id, user_id)
        return sprint


    async def get_sprint(
        self,
        db: AsyncSession,
        sprint_id: str
    ) -> SprintResponse:
   
        sprint = await self.sprint_crud.get(db, sprint_id)
        
        if not sprint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="sprint not found"
            )
        
        return SprintResponse(
            id=sprint.id,
            name=sprint.name,
            goal=sprint.goal,
            status=sprint.status,
            capacity=sprint.capacity,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            created_at=sprint.created_at,
            updated_at=sprint.updated_at,
            created_by=sprint.created_by,
            updated_by=sprint.updated_by
        )
    
    async def end_sprint(
        self,
        db: AsyncSession,
        sprint_id: str,
        user_id: str,
        end_sprint_data: SprintEnd
    ):
        """
        Soft-delete a project (manager only).
        """
        sprint = await self.sprint_crud.get(db, sprint_id)
        if not sprint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sprint not found")
        open_issues_options = {
            "backlog": self.move_open_issues_to_backlog,
            "next_sprint": self.move_open_issues_to_next_sprint,
            "new_sprint": self.move_open_issues_to_new_sprint
        }
        project = await self.project_crud.get(db, sprint.project_id)
        tasks = await self.task_crud.get_by_fields(db, fields={"sprint_id": sprint_id})
        final_state_ids = await self.workflow_state_crud.get_by_fields(
            db, 
            fields={
                "is_final": True,
                "workflow_id": project.workflow_id
            }
        )
        final_state_id = final_state_ids[0]
        move_issues_func = open_issues_options.get(end_sprint_data.move_open_issues_to.value)
        await move_issues_func(
            db,
            user_id,
            tasks,
            final_state_id.id,
            next_sprint_id=end_sprint_data.next_sprint,
            new_sprint_data=end_sprint_data.new_sprint
        )
        await self.sprint_crud.update(
            db,
            db_obj=sprint,
            obj_in={"status": "completed"},
            updated_by=user_id,
        )
        return sprint
    
    async def move_open_issues_to_backlog(
        self,
        db: AsyncSession,
        user_id: str,
        tasks: list[Task],
        final_state_id: str,
        **kwargs
    ):
        for task in tasks:
            if str(task.workflow_state_id) != str(final_state_id):
                await self.task_crud.update(
                    db,
                    db_obj=task,
                    obj_in={"sprint_id": None},
                    updated_by=user_id,
                )
        return True

    async def move_open_issues_to_next_sprint(
        self,
        db: AsyncSession,
        user_id: str,
        tasks: list[Task],
        final_state_id: str,
        **kwargs
    ):
        next_sprint_id = kwargs.get("next_sprint_id")
        for task in tasks:
            if str(task.workflow_state_id) != str(final_state_id):
                await self.task_crud.update(
                    db,
                    db_obj=task,
                    obj_in={"sprint_id": next_sprint_id},
                    updated_by=user_id,
                )
        return True
    
    async def move_open_issues_to_new_sprint(
        self,
        db: AsyncSession,
        user_id: str,
        tasks: list[Task],
        final_state_id: str,
        **kwargs
    ):
        new_sprint_data = kwargs.get("new_sprint_data")
        new_sprint = await self.create_sprint(db, user_id, new_sprint_data)
        for task in tasks:
            if str(task.workflow_state_id) != str(final_state_id):
                await self.task_crud.update(
                    db,
                    db_obj=task,
                    obj_in={"sprint_id": new_sprint.id},
                    updated_by=user_id,
                )
        return new_sprint
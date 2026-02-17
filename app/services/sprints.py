from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.tenant import Sprint, Task
from app.schemas.sprint_schemas import SprintCreate, SprintResponse, SprintUpdate
from app.services.crud import CRUDService
from app.services.task import TaskService 

class SprintService:

    def __init__(self):
        self.sprint_crud = CRUDService(Sprint)
        self.task_crud = CRUDService(Task)
        self.task_service = TaskService()


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
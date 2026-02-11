from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from typing import List, Optional
from app.db.models import Project, ProjectMember, Workflow
from app.services.workflow import WorkflowService
from app.services.team import TeamService
from app.schemas.project_schemas import ProjectCreate, CreateProjectMember
from app.services.crud import CRUDService


class ProjectService:

    def __init__(self):
        self.workflow_service = WorkflowService()
        self.team_service = TeamService()
        self.project_crud = CRUDService(Project)

    async def create_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        data: ProjectCreate
    ):
        """
        Create a new project, assign creator as manager,
        and auto-create a default workflow.
        """
        if data.code:
            existing = await self.project_crud.get_by_field(
                db,
                field="code",
                value=data.code,
                tenant_id=tenant_id
            )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project with this code already exists"
            )
        project = await self.project_crud.create(
            db,
            obj_in=data.model_dump(),
            tenant_id=tenant_id
        )

        member_data = CreateProjectMember(
            project_id=project.id,
            staff_id=user_id,
            role="project_manager"
        )
        # Assign user as PROJECT MANAGER
        await self.team_service.add_member(
            db=db,
            data=member_data,
            tenant_id=tenant_id
        )

        # Create default workflow (Todo → In Progress → Review → Done)
        await self.workflow_service.create_default_workflow(
            db=db,
            project_id=project.id,
            tenant_id=tenant_id
        )

        return project


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

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from typing import List, Optional
from app.models.tenant import Project, ProjectMember, Workflow, StaffProfile, Designation
from app.services.workflow import WorkflowService
from app.services.team import TeamService
from app.schemas.project_schemas import ProjectCreate, CreateProjectMember
from app.services.crud import CRUDService
from app.schemas.project_schemas import ProjectResponse


class ProjectService:

    def __init__(self):
        self.workflow_service = WorkflowService()
        self.team_service = TeamService()
        self.project_crud = CRUDService(Project)
        self.staff_crud = CRUDService(StaffProfile)
        self.project_member_crud = CRUDService(ProjectMember)

    async def create_project(
        self,
        db: AsyncSession,
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
                value=data.code
            )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project with this code already exists"
            )
        data.created_by = user_id
        project = await self.project_crud.create(
            db,
            obj_in=data.model_dump()
        )

        member_data = CreateProjectMember(
            project_id=project.id,
            staff_id=data.project_manager_id,
            role="project_manager"
        )
        # Assign user as PROJECT MANAGER
        await self.team_service.add_member(
            db=db,
            data=member_data,
            user_id=user_id
        )
        print('member added')
        # Create default workflow (Todo → In Progress → Review → Done)
        await self.workflow_service.create_default_workflow(
            db=db,
            project_id=project.id,
            user_id=user_id
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


    async def list_projects(
        self,
        db: AsyncSession,
        tenant_id: str
    ) -> List[Project]:

        result = await db.execute(
            select(Project).where(Project.tenant_id == tenant_id, Project.is_archived == False)
        )
        return result.scalars().all()

    async def get_project(
        self,
        db: AsyncSession,
        project_id: str
    ):
        """
        Get a specific project by ID.
        """
        project = await self.project_crud.get(db, project_id)
    
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        manager = await self.staff_crud.get(db, project.project_manager_id)
        result = await db.execute(
            select(
                ProjectMember.id,
                ProjectMember.staff_id,
                ProjectMember.role,
                StaffProfile.first_name,
                StaffProfile.last_name,
            )
            .join(StaffProfile, ProjectMember.staff_id == StaffProfile.id)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.is_active == True,
                ProjectMember.is_deleted == False,
                ProjectMember.is_removed == False
            )
        )

        result = result.all()
        print("members asd",result)
        project_members = [
            {
                "id": member[0],
                "staff_id": member[1],
                "role": member[2],
                "name": f"{member[3]} {member[4]}",
            }
            for member in result
        ]
        return ProjectResponse(
            id=project.id,
            name=project.name,
            code=project.code,
            description=project.description,
            status=project.status,
            priority=project.priority,
            project_type=project.project_type,
            manager_name=f"{manager.first_name} {manager.last_name}",
            project_members=project_members,
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


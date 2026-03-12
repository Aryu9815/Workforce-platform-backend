from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.models.tenant import Project, ProjectMember, StaffProfile
from app.services.workflow import workflow_service
from app.services.team import team_service
from app.schemas import ProjectCreate, CreateProjectMember, ProjectUpdate, ProjectResponse, PaginationParams
from datetime import datetime, timedelta, timezone
from app.services.crud import project_crud, staff_crud, sprint_crud
from app.core.constants import PROJECT_NOT_FOUND

class ProjectService:

    def __init__(self):
        """Future implementation"""
        pass

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
        existing =None
        if data.code:
            existing = await project_crud.get_by_field(
                db,
                field="code",
                value=data.code
            )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project with this code already exists"
            )
        # Create default workflow (Todo → In Progress → Review → Done)
        workflow = await workflow_service.create_default_workflow(
            db=db,
            user_id=user_id
        )
        data.workflow_id = workflow.id
        # Create project
        project = await project_crud.create(
            db,
            obj_in=data.model_dump(),
            user_id=user_id
        )

        member_data = CreateProjectMember(
            project_id=project.id,
            staff_id=data.project_manager_id,
            role="Project Manager"
        )
        # Assign user as PROJECT MANAGER
        await team_service.add_member(
            db=db,
            data=member_data,
            user_id=user_id
        )

        # Assign create default sprint
        for i in range(1, 4): # create first 3 sprints
             await sprint_crud.create(
                db,
                obj_in={
                    "name": f"Sprint {i}",
                    "goal": f"This is sprint {i}.",
                    "status": "active" if i == 1 else "planned",
                    "project_id": project.id,
                    "sprint_number": i,
                    "start_date": (datetime.now(timezone.utc).date() + timedelta(days=(i-1)*14)),
                    "end_date": (datetime.now(timezone.utc).date() + timedelta(days=i*14)),
                },
                user_id=user_id
            )

        return project


    async def update_project(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str,
        data: ProjectUpdate
    ):
        """
        Update project details (allowed only for project managers).
        """
        project = await project_crud.get(db, project_id)
    
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PROJECT_NOT_FOUND
            )
        updated_project = await project_crud.update(
            db,
            db_obj=project,
            obj_in=data.model_dump(exclude_unset=True),
            updated_by=user_id
        )

        await db.commit()
        await db.refresh(project)
        return updated_project


    async def delete_project(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str
    ):
        """
        Soft-delete a project (manager only).
        """
        project = await project_crud.delete(
            db,
            id=project_id,
            user_id=user_id,
            soft=True
        )
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PROJECT_NOT_FOUND
            )
        await team_service.delete_project_members(db, project_id, user_id) # delete project members
        await workflow_service.delete_workflow(db, project.workflow_id, user_id) # delete workflow
        await db.commit()
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

    async def get_project(
        self,
        db: AsyncSession,
        project_id: str
    ):
        """
        Get a specific project by ID.
        """
        project = await project_crud.get(db, project_id)
    
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=PROJECT_NOT_FOUND
            )

        manager = await staff_crud.get(db, project.project_manager_id)
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
            workflow_id=project.workflow_id,
            created_at=project.created_at,
            updated_at=project.updated_at
        )

    async def get_project_list(self,
        db: AsyncSession,
        pagination: PaginationParams,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        search: Optional[str] = None
    ):
        filters = {}
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority
        
        total = await project_crud.count(db, filters=filters)
        
        projects = await project_crud.get_multi(
            db,
            skip=pagination.skip,
            limit=pagination.limit,
            filters=filters,
            search_fields=['name', 'code'] if search else None,
            search_values=[search, search] if search else None
        )
        
        project_responses = []
        for project in projects:
            project_responses.append(ProjectResponse(
                id=project.id,
                name=project.name,
                code=project.code,
                description=project.description,
                status=project.status,
                priority=project.priority,
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
                updated_at=project.updated_at,
                manager_name=None,
                workflow_id=project.workflow_id,
            ))
        return project_responses, total

project_service = ProjectService()
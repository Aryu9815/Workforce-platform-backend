from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tenant import ProjectMember, StaffProfile
from app.schemas import CreateProjectMember, UpdateProjectMember
from app.services.crud import project_member_crud
from fastapi import HTTPException, status
from datetime import datetime, timezone

class TeamService:

    def __init__(self):
        """Future implementation"""
        pass


    async def add_member(self, db: AsyncSession, data: CreateProjectMember, user_id: str):
        """
        Create a new project, assign creator as manager,
        and auto-create a default workflow.
        """
        existed_member = await project_member_crud.get_by_fields(
            db,
            fields={
                "project_id": data.project_id,
                "staff_id": data.staff_id
            }
        )
        if existed_member:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member already exists")
        member = await project_member_crud.create(db, obj_in=data.model_dump(), user_id=user_id)
        await db.commit()    
        return member


    async def remove_member(self, db: AsyncSession, member_id: str, user_id: str):
        
        member = await project_member_crud.update_by_id(
            db, 
            id=member_id, 
            obj_in={
                "is_removed": True, 
                "left_at": datetime.now(timezone.utc),
            },
            updated_by=user_id
        )
        await db.commit()
        await db.refresh(member)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        return member

    async def get_project_members(self, db: AsyncSession, project_id: str):
        result = await db.execute(
            select(
                ProjectMember.id,
                ProjectMember.staff_id,
                ProjectMember.role,
                StaffProfile.first_name,
                StaffProfile.last_name,
                ProjectMember.joined_at,
                ProjectMember.left_at
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
        members = [
            {
                "id": member[0],
                "staff_id": member[1],
                "role": member[2],
                "name": f"{member[3]} {member[4]}",
                "joined_at": member[5],
                "left_at": member[6]
            }
            for member in result
        ]
        return members
    
    async def update_member(self, db: AsyncSession, member_id: str, data: UpdateProjectMember, user_id: str):
        member = await project_member_crud.update_by_id(db, id=member_id, obj_in=data.model_dump(exclude_unset=True), updated_by=user_id)
        await db.commit()
        await db.refresh(member)
        if not member:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
        return member
    
    async def delete_project_members(self, db: AsyncSession, project_id: str, user_id: str):

        members = await project_member_crud.delete_by_field(
            db, 
            field="project_id", 
            value=project_id, 
            user_id= user_id,
            soft=True
        )
        await db.commit()
        return members

team_service = TeamService()
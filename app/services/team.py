from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from app.models.tenant import ProjectMember, StaffProfile
from app.schemas.project_schemas import ProjectMemberBase, CreateProjectMember
from app.services.crud import CRUDService



class TeamService:

    def __init__(self):
        self.project_member_crud = CRUDService(ProjectMember)


    async def add_member(self, db: AsyncSession, data: CreateProjectMember, user_id: str):
        data.created_by = user_id
        member = await self.project_member_crud.create(db, obj_in=data.model_dump())
        await db.commit()    
        return member


    async def remove_member(self, db: AsyncSession, member_id: str):
        
        member = await self.project_member_crud.get(db,member_id)
        if not member:
            raise Exception(status=404, detail="Member not found")
        member.is_removed = True
        db.add(member)
        await db.commit()

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
    

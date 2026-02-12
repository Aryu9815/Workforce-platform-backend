from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from app.models.tenant import ProjectMember
from app.schemas.project_schemas import ProjectMemberBase, CreateProjectMember
from app.services.crud import CRUDService



class TeamService:

    def __init__(self):
        self.project_member_crud = CRUDService(ProjectMember)


    async def add_member(self, db: AsyncSession, data: CreateProjectMember):
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


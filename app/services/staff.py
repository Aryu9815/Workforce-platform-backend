from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4
from typing import List
from app.models.tenant import Project, StaffProfile
from app.services.crud import CRUDService


class StaffService:

    def __init__(self):
        self.staff_crud = CRUDService(StaffProfile)

    async def list_staff_names(
        self,
        db: AsyncSession
    ) -> List[Project]:

        result = await db.execute(
            select(StaffProfile.id,StaffProfile.first_name, StaffProfile.last_name)
            .filter(StaffProfile.is_active == True, StaffProfile.is_deleted == False)
        )
        staffs = result.all()
        print('1476',staffs)
        return [
            {
                "id": staff[0],
                "name": f"{staff[1]} {staff[2]}"
            }
            for staff in staffs
        ]

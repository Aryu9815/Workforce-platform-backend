from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tenant import Project, StaffProfile
from typing import List, Optional
from app.schemas import PaginationParams
from app.schemas.staff import StaffResponse
from app.schemas.department import DepartmentResponse
from  app.services.crud import staff_crud, department_crud, designation_crud
from uuid import UUID
from app.utils.cache_utils import cache_utils


class StaffService:

    async def list_staff_names(
        self,
        db: AsyncSession,
        user_id: str,
        tenant_id: str
    ) -> List[Project]:

        cached_staffs = await cache_utils.get_or_set_all_staff_base_data(db, tenant_id)
        if cached_staffs:
            return list(filter(lambda staff: staff["user_id"] != user_id, cached_staffs))
        
        result = await db.execute(
            select(StaffProfile.id,StaffProfile.first_name, StaffProfile.last_name)
            .filter(StaffProfile.is_active == True, StaffProfile.is_deleted == False, StaffProfile.user_id != user_id)
        )
        staffs = result.all()
        return [
            {
                "id": staff[0],
                "name": f"{staff[1]} {staff[2]}"
            }
            for staff in staffs
        ]

    def get_department(self, db: AsyncSession, department_id: UUID):
        return department_crud.get(db, department_id)
    def get_designation(self, db: AsyncSession, designation_id: UUID):
        return designation_crud.get(db, designation_id)


    async def get_staff_list(self, 
        db: AsyncSession, 
        pagination: PaginationParams, 
        department_id: Optional[str] = None,
        status: Optional[str] = "active",
        search: Optional[str] = None,
    ):

        filters = {}
        include_inactive = status != "active"
        if department_id:
            filters["department_id"] = department_id
        
        total = await staff_crud.count(db, filters=filters, include_inactive=include_inactive)
        
        staff_list = await staff_crud.get_multi(
            db,
            skip=pagination.skip,
            limit=pagination.limit,
            search_fields=["first_name", "last_name"] if search else None,
            search_values=[search, search] if search else None,
            include_inactive=include_inactive,
            filters=filters
        )
        
        # Convert to response schema
        staff_responses = []
        for staff in staff_list:
            department = await self.get_department(db, staff.department_id) if staff.department_id else None
            designation = await self.get_designation(db, staff.designation_id) if staff.designation_id else None
            department_name = department.name if department else None
            designation_name = designation.name if designation else None
            staff_responses.append(StaffResponse(
                id=staff.id,
                employee_code=staff.employee_code,
                first_name=staff.first_name,
                last_name=staff.last_name,
                email=staff.email,
                phone=staff.phone,
                department_id=staff.department_id,
                designation_id=staff.designation_id,
                reporting_manager_id=staff.reporting_manager_id,
                employment_type=staff.employment_type,
                join_date=staff.join_date,
                work_location=staff.work_location,
                user_id=staff.user_id,
                exit_date=staff.exit_date,
                exit_reason=staff.exit_reason,
                skills=staff.skills or [],
                is_active=staff.is_active,
                full_name=f"{staff.first_name} {staff.last_name}",
                created_at=staff.created_at,
                updated_at=staff.updated_at,
                created_by=staff.created_by,
                updated_by=staff.updated_by ,
                department_name= department_name ,
                designation_name=designation_name
            ))
        return staff_responses, total
    
    async def generate_employee_code(self, db: AsyncSession, tenant_code: str, dept_code: str) -> str:
        prefix = f"{tenant_code}{dept_code}"
        
        # Query last employee with same prefix
        query = select(StaffProfile.employee_code).where(
            StaffProfile.employee_code.ilike(f"{prefix}%")
        ).order_by(StaffProfile.employee_code.desc()).limit(1)

        result = await db.execute(query)
        last_code = result.scalar_one_or_none()

        if last_code:
            # Extract numeric part
            numeric = last_code.replace(prefix, "")
            next_number = int(numeric) + 1
        else:
            next_number = 1 

        return f"{prefix}{next_number}"

    async def get_departments(self, db: AsyncSession):
        departments = await department_crud.get_multi(
            db,
            filters={"is_active": True}
        )
        
        return [
            DepartmentResponse(
                id=dept.id,
                name=dept.name,
                code=dept.code,
                description=dept.description,
                parent_id=dept.parent_id,
                head_id=dept.head_id,
                is_active=dept.is_active,
                created_at=dept.created_at,
                updated_at=dept.updated_at,
                staff_count= await staff_crud.count(
                    db,
                    filters={"department_id": dept.id}
                )
            )
            for dept in departments
        ]

staff_service = StaffService()
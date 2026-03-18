from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.constants import STAFF_NOT_FOUND
from app.models.tenant import Project, StaffProfile
from typing import List, Optional
from app.schemas import PaginationParams
from app.schemas import DepartmentResponse, DesignationResponse, StaffResponse
from  app.services.crud import (
    staff_crud, department_crud, designation_crud, tenant_user_role_crud, 
    attendance_crud, user_crud, tenant_master_crud, tenant_user_crud
)
from uuid import UUID
from app.utils.cache_utils import cache_utils
from app.utils.db_utils import get_staff


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

    async def get_department(self, db: AsyncSession, tenant_id: UUID):

        department_names = await cache_utils.get_all_departments_cache(tenant_id)
        if department_names:
            return department_names
        
        departments = await department_crud.get_multi(
            db,
            filters={"is_active": True}
        )
        
        department_names = {str(dept.id): dept.name for dept in departments}
        await cache_utils.set_all_departments_cache(tenant_id, department_names)
        return department_names
    
    async def get_designation(self, db: AsyncSession, tenant_id: UUID):
        designation_names = await cache_utils.get_all_designations_cache(tenant_id)
        if designation_names:
            return designation_names
        
        designations = await designation_crud.get_multi(
            db,
            filters={"is_active": True}
        )
        
        designation_names = {str(designation.id): designation.name for designation in designations}
        await cache_utils.set_all_designations_cache(tenant_id, designation_names)
        return designation_names
    


    async def get_staff_list(self, 
        db: AsyncSession, 
        pagination: PaginationParams, 
        department_id: Optional[str] = None,
        status: Optional[str] = "active",
        search: Optional[str] = None,
        tenant_id: UUID = None
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
        departments = await self.get_department(db, tenant_id)
        designations = await self.get_designation(db, tenant_id)
        for staff in staff_list:
            staff_responses.append({
                "id":staff.id,
                "employee_code":staff.employee_code,
                "email":staff.email,
                "profile_image":staff.profile_image,
                "first_name":staff.first_name,
                "last_name":staff.last_name,
                "phone":staff.phone,
                "user_id":staff.user_id,
                "is_active":staff.is_active,
                "department_name": departments.get(str(staff.department_id)),
                "designation_name":designations.get(str(staff.designation_id))
            })
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

    async def get_departments(self, db: AsyncSession, for_dropdown: bool = False, tenant_id: UUID = None):
        if for_dropdown:
            departments = await cache_utils.get_all_departments_cache(tenant_id)
            if departments:
                return [{"id":k, "name":v} for k,v in departments.items()]
            
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
    
    async def get_designations(self, db: AsyncSession, for_dropdown: bool = False, tenant_id: UUID = None):
        if for_dropdown:
            designations = await cache_utils.get_all_designations_cache(tenant_id)
            if designations:
                return [{"id":k, "name":v} for k,v in designations.items()]
            
        designations = await designation_crud.get_multi(
            db,
            filters={"is_active": True} , 
            order_by="name"
        )

        return [
            DesignationResponse(
                id=d.id,
                name=d.name,
                level=d.level,
                department_id=d.department_id,
                description=d.description,
                is_active=d.is_active,
                created_at=d.created_at,
                updated_at=d.updated_at
            )
            for d in designations
        ]

    async def get_staff_data(self, db: AsyncSession, staff_id: UUID, tenant_id: UUID):
        staff = await get_staff(db, staff_id, tenant_id)
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=STAFF_NOT_FOUND
            )
        designation = await designation_crud.get(db, staff.designation_id)
        department = await department_crud.get(db, staff.department_id)
        role_id = await tenant_user_role_crud.get_by_field(db, field="user_id", value=staff.user_id)

        return StaffResponse(
            id=staff.id,
            employee_code=staff.employee_code,
            first_name=staff.first_name,
            last_name=staff.last_name,
            profile_image=staff.profile_image,
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
            designation_name=designation.name if designation else None,
            department_name=department.name if department else None,
            role_id=role_id.role_id if role_id else None
        )

    async def get_profile(self, db: AsyncSession, common_db: AsyncSession, staff_id: UUID, tenant_id: UUID):
        staff = await get_staff(db, staff_id, tenant_id)
        if not staff:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=STAFF_NOT_FOUND)
        departments = await self.get_department(db, tenant_id)
        designations = await self.get_designation(db, tenant_id)
        manager = await get_staff(db, staff.reporting_manager_id, tenant_id)

        attendance_records = await attendance_crud.get_multi(
            db,
            limit=-1,
            filters={"staff_id": staff.id}
        )
        user = await tenant_user_crud.get(db, staff.user_id)
        master_user = await user_crud.get(common_db, user.user_id)
        tenants = []
        
        for id in master_user.tenant_ids:            
            tenant = await tenant_master_crud.get_by_field(common_db, field="tenant_id", value=id)
            tenants.append(tenant)

        return {
            "first_name": staff.first_name,
            "last_name": staff.last_name,
            "email": staff.email,
            "phone": staff.phone,
            "department": departments[str(staff.department_id)],
            "designation": designations[str(staff.designation_id)],
            "work_location": staff.work_location,
            "employment_type": staff.employment_type,
            "skills": staff.skills,
            "profile_image": staff.profile_image,
            "reporting_manager_id": staff.reporting_manager_id,
            "reporting_manager_code": manager.employee_code if manager else None,
            "reporting_manager": f"{manager.first_name} {manager.last_name}" if manager else None,
            "join_date": staff.join_date,
            "exit_date": staff.exit_date,
            "exit_reason": staff.exit_reason,
            "is_active": staff.is_active,
            "employee_code": staff.employee_code,
            "user_id": staff.user_id,
            "id": staff.id,
            "attendance_records": [
                {
                    "date": record.date,
                    "status":record.status,
                    "work_hours":(record.work_hours or 0) + (record.overtime_hours or 0),
                    "check_in":record.check_in,
                    "check_out":record.check_out
                }
                for record in attendance_records
            ],
            "tenants": [
                {
                    "id":tenant.tenant_id,
                    "name":tenant.tenant_name,
                    "code":tenant.tenant_code,
                    "is_active":tenant.is_active,
                }
                for tenant in tenants
            ]
        
        }
         
staff_service = StaffService()
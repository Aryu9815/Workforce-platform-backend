import json
from sqlalchemy import select
from app.core.security import hash_password
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.models.common import User
from app.models.tenant import TenantUserRole, TenantUser, StaffProfile, Department, Designation
from app.schemas import (
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    StaffCreate,
    StaffUpdate,
    StaffResponse,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
)
from app.db.base import get_db_session, get_common_db
from app.services.crud import (
    tenant_master_crud, staff_crud, 
    department_crud, designation_crud, tenant_user_role_crud
)
from app.core.logging_config import get_logger
from app.services import staff_service, notify, leave_initialization_service as leave_init_service
from app.utils.rbac_middleware import require_permissions
from app.core.constants import STAFF_NOT_FOUND, IMAGE_DIR
from app.api.routes.roles import _check_role_exists
from app.utils.cache_utils import cache_utils
from app.utils.db_utils import get_staff
from app.utils.image_utils import save_image
from fastapi.responses import FileResponse
import os

logger = get_logger(__name__)
router = APIRouter(prefix="/staff", tags=["Staff Management"])


@router.get("", response_model=PaginatedResponse)
@require_permissions(["staff:view"])
async def list_staff(
    request: Request,
    pagination: PaginationParams = Depends(),
    department_id: Optional[UUID] = None,
    status: Optional[str] = "active",
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all staff members with filtering."""
    staff_responses, total = await staff_service.get_staff_list(
        db,
        pagination,
        department_id,
        status,
        search,
        tenant_id=getattr(request.state, 'tenant_id', None)
    )
    
    return PaginatedResponse.create(
        items=staff_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )

async def _staff_exist(db, email, phone = None):
    result = await db.execute(
            select(StaffProfile).where(
                StaffProfile.email == email,
                StaffProfile.is_deleted == False
            )
        )
    existing_staff = result.scalar_one_or_none()

    if existing_staff:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Staff already exists in this tenant"
        )
    
    if phone:
        result = await db.execute(
            select(StaffProfile).where(
                StaffProfile.phone == str(phone),
                StaffProfile.is_deleted == False
            )
        )
        existing_staff = result.scalar_one_or_none()

        if existing_staff:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already registered in this tenant"
            )

async def _user_tenant_mapping(db, user_id, tenant_id):
    result = await db.execute(
        select(TenantUser).where(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
        )
    )
    tenant_mapping = result.scalar_one_or_none()

    if tenant_mapping:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already belongs to this tenant"
        )


@router.post(
    "",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_permissions(["staff:create"])
async def create_staff(
    request: Request,
    staff_data: str = Form(...),
    profile_image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db_session),
    common_db: AsyncSession = Depends(get_common_db)
):
    
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)

    staff_data_dict = json.loads(staff_data)
    staff_data = StaffCreate.model_validate(staff_data_dict)
    async with db.begin():

        # Check if staff email already exists IN THIS TENANT
        await _staff_exist(db, staff_data.email, staff_data.phone)

        # Check if master user exists globally
        result = await common_db.execute(
            select(User).where(
                User.email == staff_data.email,
                User.is_deleted == False
            )
        )
        user = result.scalar_one_or_none()

        if user:
            # Check if already mapped to this tenant
            await _user_tenant_mapping(db, user.id, tenant_id)

            # Add tenant mapping
            tenant_user = TenantUser(
                tenant_id=tenant_id,
                user_id=user.id,
                invited_by=user_id,
                created_by=str(user_id)
            )

            db.add(tenant_user)
            await db.flush()

            # Update JSONB safely
            if str(tenant_id) not in (user.tenant_ids or []):
                user.tenant_ids = (user.tenant_ids or []) + [str(tenant_id)]

        else:
            # Create new master user
            user = User(
                email=staff_data.email,
                password_hash=hash_password("Temp@123"),
                first_name=staff_data.first_name,
                last_name=staff_data.last_name,
                phone=staff_data.phone,
                tenant_ids=[str(tenant_id)],
                
            )
            print("Creating user with this data:", user.email)

            common_db.add(user)
            await common_db.flush()

            tenant_user = TenantUser(
                tenant_id=tenant_id,
                user_id=user.id,
                invited_by=user_id,
                created_by=str(user_id),
                updated_by=str(user_id),
            )

            db.add(tenant_user)
            await db.flush()

        profile_image_path = None

        if profile_image:
            profile_image_path = await save_image(profile_image)
        # Create Staff Profile (Tenant Scoped)
        tenant = await tenant_master_crud.get_by_field(common_db, field="tenant_id", value=tenant_id)
        department = await department_crud.get(db, staff_data.department_id)
        emp_code = await staff_service.generate_employee_code(db, tenant.tenant_code, department.code)
        staff_data.employee_code = emp_code
        staff_dict = staff_data.model_dump(
           exclude={"created_by", "updated_by", "profile_image"}
        )
        role_id=staff_dict.pop("role_id", None)
        staff = StaffProfile(
            **staff_dict,
            user_id=tenant_user.id,
            created_by=str(user_id),
            updated_by=str(user_id),
            profile_image=profile_image_path
        )
        db.add(staff)
        await db.flush()

        # Assign Role (Tenant Scoped)
        if staff_data.role_id:

            # Validate role exists
            await _check_role_exists(db, role_id)

            # Check duplicate role assignment
            existing_role = await db.execute(
                select(TenantUserRole).where(
                    TenantUserRole.user_id == tenant_user.id,
                    TenantUserRole.role_id == role_id,
                )
            )

            if existing_role.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Role already assigned to this user"
                )

            tenant_user_role = TenantUserRole(
                user_id=tenant_user.id,
                role_id=role_id,
                project_id=None,
                assigned_by=user_id,
                created_by=str(user_id),
            )

            db.add(tenant_user_role)
            await db.flush()

        await leave_init_service.initialize_staff_leave_balances(
            db=db,
            staff_id=staff.id,
            join_date=staff.join_date,
            created_by=str(user_id),
        )
    
    # Fetch Related Names
    department = await db.get(Department, staff.department_id)
    designation = await db.get(Designation, staff.designation_id)
    await cache_utils.delete_all_staff(tenant_id)
    await cache_utils.get_or_set_all_staff_base_data(db, tenant_id)
    await notify.notify_staff(staff,department, designation, tenant_id, user_id)
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
        department_name=department.name if department else None,
        designation_name=designation.name if designation else None,
        reporting_manager_id=staff.reporting_manager_id,
        employment_type=staff.employment_type,
        join_date=staff.join_date,
        work_location=staff.work_location,
        user_id=user.id,
        skills=staff.skills or [],
        is_active=staff.is_active,
        full_name=f"{staff.first_name} {staff.last_name}",
        created_at=staff.created_at,
        updated_at=staff.updated_at,
        created_by=str(user_id) if user_id else None,
        updated_by=str(user_id) if user_id else None   ,
    )



# ============================================
# Department Routes
# ============================================

@router.get("/departments", response_model=List[DepartmentResponse])
@require_permissions(["department:view"])
async def list_departments(
    request: Request,
    is_dropdown: bool = False,
    db: AsyncSession = Depends(get_db_session)
):
    """List all departments."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    return await staff_service.get_departments(db, is_dropdown, tenant_id)


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(["department:create"])
async def create_department(
    request: Request,
    dept_data: DepartmentCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new department."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, "user_id", None)
    dept_data_dict = dept_data.model_dump()
    department = await department_crud.create(
        db,
        obj_in=dept_data_dict,
        user_id=user_id
    )
    await db.commit()
    await db.refresh(department)
    logger.info(f"Department created: {department.id}")
    await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': "New Department",
            'message': f"You have added a new department {department.name}"
        }
    )
    return DepartmentResponse(
        id=department.id,
        name=department.name,
        code=department.code,
        description=department.description,
        parent_id=department.parent_id,
        head_id=department.head_id,
        is_active=department.is_active,
        created_at=department.created_at,
        updated_at=department.updated_at,
        staff_count=0
    )

# ============================================
# Designation Routes
# ============================================

@router.get("/designations", response_model=List[DesignationResponse])
@require_permissions(["designation:view"])
async def list_designations(
    request: Request,
    is_dropdown: bool = False,
    db: AsyncSession = Depends(get_db_session)
):
    tenant_id = getattr(request.state, 'tenant_id', None)
    return await staff_service.get_designations(db, is_dropdown, tenant_id)


@router.post(
    "/designations",
    response_model=DesignationResponse,
    status_code=status.HTTP_201_CREATED
)
@require_permissions(["designation:create"])
async def create_designation(
    request: Request,
    designation_data: DesignationCreate,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Creating designation with data: {designation_data}")  
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, "user_id", None)
    
    designation_data_dict = designation_data.model_dump()

    designation = await designation_crud.create(
        db,
        obj_in=designation_data_dict,
        user_id=user_id
    )
    await db.commit()
    await db.refresh(designation)
    await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': "New Designation",
            'message': f"You have added a new designation {designation.name}"
        }
    )
    return DesignationResponse(
        id=designation.id,
        name=designation.name,
        level=designation.level,
        department_id=designation.department_id,
        description=designation.description,
        is_active=designation.is_active,
        created_at=designation.created_at,
        updated_at=designation.updated_at
    )

@router.put("/designations/{designation_id}", response_model=DesignationResponse)
@require_permissions(["designation:update"])
async def update_designation(
    request: Request,
    designation_id: UUID,
    designation_data: DesignationUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    if designation_data.department_id:
        designation = await designation_crud.get(
            db,
            designation_id,
        )

        if not designation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Designation not found"
            )
    current_user_id = getattr(request.state, "user_id", None)
    designation_data_dict = designation_data.model_dump(exclude_unset=True)
    designation_data_dict["updated_by"] = current_user_id
    updated = await designation_crud.update(
        db,
        db_obj=designation,
        obj_in=designation_data_dict
    )
    await db.commit()
    await db.refresh(updated)
    return DesignationResponse(
        id=updated.id,
        name=updated.name,
        level=updated.level,
        department_id=updated.department_id,
        description=updated.description,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at
    )


@router.put("/departments/{department_id}", response_model=DepartmentResponse)
@require_permissions(["department:update"])
async def update_department(
    request: Request,
    department_id: UUID,
    dept_data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a department."""
    current_user_id = getattr(request.state, "user_id", None)
    
    department = await department_crud.get(db, department_id)
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    dept_data_dict = dept_data.model_dump(exclude_unset=True)
    dept_data_dict["updated_by"] = current_user_id
    updated_dept = await department_crud.update(
        db,
        db_obj=department,
        obj_in=dept_data_dict
    )
    
    logger.info(f"Department updated: {updated_dept.id}")
    await db.commit()
    await db.refresh(updated_dept)
    return DepartmentResponse(
        id=updated_dept.id,
        name=updated_dept.name,
        code=updated_dept.code,
        description=updated_dept.description,
        parent_id=updated_dept.parent_id,
        head_id=updated_dept.head_id,
        is_active=updated_dept.is_active,
        created_at=updated_dept.created_at,
        updated_at=updated_dept.updated_at,
        staff_count=0
    )

@router.get("/{staff_id:uuid}", response_model=StaffResponse)
@require_permissions(["staff:view"])
async def get_staff(
    request: Request,
    staff_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific staff member by ID."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    return await staff_service.get_staff_data(db, staff_id, tenant_id)


@router.put("/{staff_id:uuid}", response_model=StaffResponse)
@require_permissions(["staff:update"])
async def update_staff(
    request: Request,
    staff_id: UUID,
    staff_data: StaffUpdate,
    profile_image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db_session)
):
    """Update a staff member."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)           
    staff = await get_staff(db, staff_id, tenant_id)
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=STAFF_NOT_FOUND
        )
    staff_dict = staff_data.model_dump()
    role_id = staff_dict.pop("role_id", None)
    if profile_image:
        profile_image_path = await save_image(profile_image)
        staff_dict["profile_image"] = profile_image_path
    
    # Update staff
    updated_staff = await staff_crud.update(
        db,
        db_obj=staff,
        obj_in=staff_dict
    )
    
    # Assign Role (Tenant Scoped)
    if role_id:
        user_role = await tenant_user_role_crud.get_by_field(db, field="user_id", value=staff.user_id)
        user_role.role_id = role_id
        user_role.updated_by = str(user_id)
        await db.commit()
        await db.refresh(user_role)
        await db.flush()
    await db.commit()
    await db.refresh(updated_staff)
    
    await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(user_id),
            'title': "Updated Staff",
            'message': f"You have updated a staff {updated_staff.first_name} {updated_staff.last_name}"
        }
    )

    await notify.create_notification(
        data={
            'tenant_id':tenant_id,
            'user_id':str(staff.user_id),
            'title': "Staff profile updated",
            'message': "Your staff profile has been updated."
        }
    )

    logger.info(f"Staff updated: {updated_staff.id}")
    await cache_utils.delete_staff(staff.id, tenant_id)
    await cache_utils.get_or_set_all_staff_base_data(db, tenant_id)
    return StaffResponse(
        id=updated_staff.id,
        employee_code=updated_staff.employee_code,
        first_name=updated_staff.first_name,
        last_name=updated_staff.last_name,
        profile_image=updated_staff.profile_image,
        email=updated_staff.email,
        phone=updated_staff.phone,
        department_id=updated_staff.department_id,
        designation_id=updated_staff.designation_id,
        reporting_manager_id=updated_staff.reporting_manager_id,
        employment_type=updated_staff.employment_type,
        join_date=updated_staff.join_date,
        work_location=updated_staff.work_location,
        user_id=updated_staff.user_id,
        exit_date=updated_staff.exit_date,
        exit_reason=updated_staff.exit_reason,
        skills=updated_staff.skills or [],
        is_active=updated_staff.is_active,
        full_name=f"{updated_staff.first_name} {updated_staff.last_name}",
        created_at=updated_staff.created_at,
        updated_at=updated_staff.updated_at,
    )


@router.delete("/{staff_id:uuid}", response_model=SuccessResponse)
@require_permissions(["staff:delete"])
async def delete_staff(
    request: Request,
    staff_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a staff member."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    staff = await staff_crud.delete(
        db,
        id=staff_id,
        soft=True,
        user_id=user_id
    )
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=STAFF_NOT_FOUND
        )
    
    await notify.notify_staff_remove(staff, tenant_id, user_id)
    logger.info(f"Staff deleted: {staff_id}")
    await cache_utils.delete_staff(staff_id, tenant_id)
    return SuccessResponse(message="Staff member deleted successfully")

@router.get("/get-names")
async def get_staff_names(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """Get staff names by IDs."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)

    names = await staff_service.list_staff_names(db, user_id, tenant_id)
    return names

@router.get("/profile-image/{filename}")
async def get_profile_image(
    request: Request,
    filename: str
    ):

    file_path = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(file_path)

@router.get("/{staff_id:uuid}/get_profile")
async def get_profile(
    request: Request,
    staff_id: UUID,
    common_db: AsyncSession = Depends(get_common_db),
    db: AsyncSession = Depends(get_db_session)
):
    tenant_id = getattr(request.state, 'tenant_id', None)
    return await staff_service.get_profile(db, common_db, staff_id, tenant_id)
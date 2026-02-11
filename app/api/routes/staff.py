"""
Staff management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.middleware.auth import AuthMiddleware
from app.api.schemas import (
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
    StaffCreate,
    StaffUpdate,
    StaffResponse,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse
)
from app.db.models import StaffProfile, Department, Designation
from app.db.base import get_db_session
from app.services.crud import CRUDService
from app.services.auth import auth_service
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/staff", tags=["Staff Management"])

# CRUD services
staff_crud = CRUDService(StaffProfile)
department_crud = CRUDService(Department)
designation_crud = CRUDService(Designation)

def get_department( db: AsyncSession, department_id: UUID, tenant_id: UUID):
    return department_crud.get(db, department_id, tenant_id=tenant_id)
def get_designation(db: AsyncSession, designation_id: UUID, tenant_id: UUID):
    return designation_crud.get(db, designation_id, tenant_id=tenant_id)
@router.get("", response_model=PaginatedResponse)
async def list_staff(
    request: Request,
    pagination: PaginationParams = Depends(),
    department_id: Optional[UUID] = None,
    status: Optional[str] = "active",
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List all staff members with filtering."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    filters = {"is_active": True if status == "active" else False}
    if department_id:
        filters["department_id"] = department_id
    
    # Get total count
    total = await staff_crud.count(db, tenant_id=tenant_id, filters=filters)
    
    # Get staff list
    staff_list = await staff_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        tenant_id=tenant_id,
        filters=filters
    )
    
    # Convert to response schema
    staff_responses = []
    for staff in staff_list:
        department = await get_department(db, staff.department_id, tenant_id) if staff.department_id else None
        designation = await get_designation(db, staff.designation_id, tenant_id) if staff.designation_id else None
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
            department_name= department_name ,  # TODO: Fetch department name
            designation_name=designation_name  # TODO: Fetch designation name
        ))
    
    return PaginatedResponse.create(
        items=staff_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )

def require_auth_context(request: Request):
    if not getattr(request.state, "user_id", None):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return request

@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    request: Request ,
    staff_data: StaffCreate ,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new staff member."""
    logger.info(f"Creating staff with data: {staff_data}")
    print(f"Creating staff with data: {staff_data}")
    # tenant_id = getattr(request.state, 'tenant_id', None)
    tenant_id ="11111111-1111-1111-1111-111111111111"
    print(f"Tenant ID from request state: {tenant_id}")
    if not tenant_id:
        raise HTTPException(
            status_code=400,
            detail="Tenant context missing"
        )

    user_id = getattr(request.state, 'user_id', None)
    
    # Check if email already exists in tenant
    existing = await staff_crud.get_by_field(
        db,
        field="email",
        value=staff_data.email,
        tenant_id=tenant_id
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Staff member with this email already exists"
        )
    
    # Create staff
    staff = await staff_crud.create(
        db,
        obj_in=staff_data.model_dump(),
        tenant_id=tenant_id
    )
    
    # Publish event
    await publish_event(
        event_type=EventType.STAFF_CREATED,
        aggregate_type="staff",
        aggregate_id=str(staff.id),
        tenant_id=tenant_id,
        payload={
            "employee_code": staff.employee_code,
            "email": staff.email,
            "name": f"{staff.first_name} {staff.last_name}",
            "department_id": str(staff.department_id)if staff.department_id else None,
            "created_by": user_id
        }
    )
    department_crud = CRUDService(Department)
    designation_crud = CRUDService(Designation)
    department =  await department_crud.get(db, staff.department_id, tenant_id=tenant_id) if staff.department_id else None
    designation = await designation_crud.get(db, staff.designation_id, tenant_id=tenant_id) if staff.designation_id else None
    staff.department_name =  department.name if department else None
    staff.designation_name = designation.name if designation else None
    print(f"Staff created with ID: {staff.id}, Department: {staff.department_name}, Designation: {staff.designation_name}")

    logger.info(f"Staff created: {staff.id}")
    
    return StaffResponse(
        id=staff.id,
        employee_code=staff.employee_code,
        first_name=staff.first_name,
        last_name=staff.last_name,
        email=staff.email,
        phone=staff.phone,
        department_id=staff.department_id,
        designation_id=staff.designation_id,
        department_name=staff.department_name,
        designation_name=staff.designation_name,
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
        updated_at=staff.updated_at
    )



# ============================================
# Department Routes
# ============================================

@router.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """List all departments."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    departments = await department_crud.get_multi(
        db,
        tenant_id=tenant_id,
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
            staff_count=0  # TODO: Calculate staff count
        )
        for dept in departments
    ]


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    request: Request,
    dept_data: DepartmentCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new department."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    department = await department_crud.create(
        db,
        obj_in=dept_data.model_dump(),
        tenant_id=tenant_id
    )
    
    logger.info(f"Department created: {department.id}")
    
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
async def list_designations(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    tenant_id = getattr(request.state, 'tenant_id', None)

    designations = await designation_crud.get_multi(
        db,
        tenant_id=tenant_id,
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
@router.post(
    "/designations",
    response_model=DesignationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_designation(
    request: Request,
    designation_data: DesignationCreate,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Creating designation with data: {designation_data}")  
    print(f"Creating designation with data: {designation_data}")
    tenant_id = getattr(request.state, 'tenant_id', None)

    designation = await designation_crud.create(
        db,
        obj_in=designation_data.model_dump(),
        tenant_id=tenant_id
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
async def update_designation(
    request: Request,
    designation_id: UUID,
    designation_data: DesignationUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    tenant_id = getattr(request.state, 'tenant_id', None)
    if designation_data.department_id:
        designation = await designation_crud.get(
            db,
            designation_id,
            tenant_id=tenant_id
        )

        if not designation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Designation not found"
            )

    updated = await designation_crud.update(
        db,
        db_obj=designation,
        obj_in=designation_data.model_dump(exclude_unset=True)
    )

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
async def update_department(
    request: Request,
    department_id: UUID,
    dept_data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a department."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    department = await department_crud.get(db, department_id, tenant_id=tenant_id)
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    updated_dept = await department_crud.update(
        db,
        db_obj=department,
        obj_in=dept_data.model_dump(exclude_unset=True)
    )
    
    logger.info(f"Department updated: {updated_dept.id}")
    
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

@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff(
    request: Request,
    staff_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific staff member by ID."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    staff = await staff_crud.get(db, staff_id, tenant_id=tenant_id)
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    return StaffResponse(
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
        updated_at=staff.updated_at
    )


@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    request: Request,
    staff_id: UUID,
    staff_data: StaffUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update a staff member."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    staff = await staff_crud.get(db, staff_id, tenant_id=tenant_id)
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    # Update staff
    updated_staff = await staff_crud.update(
        db,
        db_obj=staff,
        obj_in=staff_data.model_dump(exclude_unset=True)
    )
    
    # Publish event
    await publish_event(
        event_type=EventType.STAFF_UPDATED,
        aggregate_type="staff",
        aggregate_id=str(updated_staff.id),
        tenant_id=tenant_id,
        payload={
            "employee_code": updated_staff.employee_code,
            "updated_by": user_id,
            "changes": staff_data.model_dump(exclude_unset=True)
        }
    )
    
    logger.info(f"Staff updated: {updated_staff.id}")
    
    return StaffResponse(
        id=updated_staff.id,
        employee_code=updated_staff.employee_code,
        first_name=updated_staff.first_name,
        last_name=updated_staff.last_name,
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
        updated_at=updated_staff.updated_at
    )


@router.delete("/{staff_id}", response_model=SuccessResponse)
async def delete_staff(
    request: Request,
    staff_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Soft delete a staff member."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    staff = await staff_crud.delete(
        db,
        id=staff_id,
        tenant_id=tenant_id,
        soft=True
    )
    
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    # Publish event
    await publish_event(
        event_type=EventType.STAFF_DELETED,
        aggregate_type="staff",
        aggregate_id=str(staff_id),
        tenant_id=tenant_id,
        payload={
            "employee_code": staff.employee_code,
            "deleted_by": user_id
        }
    )
    
    logger.info(f"Staff deleted: {staff_id}")
    
    return SuccessResponse(message="Staff member deleted successfully")

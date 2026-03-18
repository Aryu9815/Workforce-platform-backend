from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from app.models.tenant import Task, Project
from app.schemas import (
    ReimbursementClaimCreate,
    ReimbursementClaimUpdate,
    ReimbursementClaimResponse,
    ReimbursementItemResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse
)
from app.db.base import get_db_session
from app.services.crud import (
    staff_crud,
    claim_crud,
    reimbursement_item_crud as item_crud,
    expense_category_crud as category_crud
)
from app.core.logging_config import get_logger
from app.services import notify
from app.utils.rbac_middleware import require_permissions
from app.core.constants import CLAIM_NOT_FOUND
from app.utils.db_utils import get_staff

logger = get_logger(__name__)
router = APIRouter(prefix="/reimbursements", tags=["Reimbursement Management"])


def generate_claim_number() -> str:
    """Generate a unique claim number."""
    return f"RMB-{datetime.now().strftime('%Y%m%d%H%M%S')}"


@router.get("/claims", response_model=PaginatedResponse)
@require_permissions(["reimbursement:view", "reimbursement:view:all"])
async def list_reimbursement_claims(
    request: Request,
    pagination: PaginationParams = Depends(),
    staff_id: Optional[UUID] = None,
    status: Optional[str] = None,
    project_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List reimbursement claims with filtering."""
    permissions = getattr(request.state, "permissions", [])
    tenant_id = getattr(request.state, 'tenant_id', None)
    filters = {}
    if staff_id and "reimbursement:view:all" not in permissions:
        filters["staff_id"] = staff_id
    if status:
        filters["status"] = status
    if project_id:
        filters["project_id"] = project_id
    
    total = await claim_crud.count(db, filters=filters)
    
    claims = await claim_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )
    
    claim_responses = []
    for claim in claims:
        # Get items for this claim
        items = await item_crud.get_by_fields(
            db,
            fields={"claim_id": claim.id}
        )
        
        item_responses = [
            ReimbursementItemResponse(
                id=item.id,
                category_id=item.category_id,
                expense_date=item.expense_date,
                description=item.description,
                amount=item.amount,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_amount=item.tax_amount,
                merchant_name=item.merchant_name,
                merchant_location=item.merchant_location,
                receipt_file_id=item.receipt_file_id,
                is_billable=item.is_billable,
                created_at=item.created_at
            )
            for item in items
        ]
        staff = await get_staff(db, claim.staff_id, tenant_id)
        claim_responses.append(ReimbursementClaimResponse(
            id=claim.id,
            claim_number=claim.claim_number,
            staff_id=claim.staff_id,
            project_id=claim.project_id,
            task_id=claim.task_id,
            claim_date=claim.claim_date,
            total_amount=claim.total_amount,
            currency=claim.currency,
            description=claim.description,
            status=claim.status,
            submitted_at=claim.submitted_at,
            approved_by=claim.approved_by,
            approved_at=claim.approved_at,
            approval_notes=claim.approval_notes,
            paid_at=claim.paid_at,
            payment_reference=claim.payment_reference,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            staff_name=staff.first_name + " " + staff.last_name if staff else None,
            items=item_responses
        ))
    
    return PaginatedResponse.create(
        items=claim_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("/claims", response_model=ReimbursementClaimResponse, status_code=status.HTTP_201_CREATED)
@require_permissions(["reimbursement:create"])
async def create_reimbursement_claim(
    request: Request,
    claim_data: ReimbursementClaimCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new reimbursement claim."""
    
    # Calculate total from items
    total_amount = sum(
        item.amount for item in claim_data.items
    ) if claim_data.items else claim_data.total_amount
    current_user_id = getattr(request.state, "user_id", None)
    
    # Create claim
    claim = await claim_crud.create(
        db,
        obj_in={
            "claim_number": generate_claim_number(),
            "staff_id": claim_data.staff_id,
            "project_id": claim_data.project_id,
            "task_id": claim_data.task_id,
            "claim_date": claim_data.claim_date,
            "expense_date_start": claim_data.expense_date_start,
            "expense_date_end": claim_data.expense_date_end,
            "total_amount": total_amount,
            "currency": claim_data.currency,
            "description": claim_data.description,
            "status": "draft",
            "created_by":str(current_user_id) if current_user_id else None,
            "updated_by":str(current_user_id) if current_user_id else None   ,
        }
    )
    
    # Create items
    for item_data in claim_data.items:
        await item_crud.create(
            db,
            obj_in={
                **item_data.model_dump(),
                "claim_id": claim.id,
                "created_by":str(current_user_id) if current_user_id else None,
                "updated_by":str(current_user_id) if current_user_id else None   ,

            }        )
    
    logger.info(f"Reimbursement claim created: {claim.id}")
    
    return ReimbursementClaimResponse(
        id=claim.id,
        claim_number=claim.claim_number,
        staff_id=claim.staff_id,
        project_id=claim.project_id,
        task_id=claim.task_id,
        claim_date=claim.claim_date,
        total_amount=claim.total_amount,
        currency=claim.currency,
        description=claim.description,
        status=claim.status,
        submitted_at=claim.submitted_at,
        approved_by=claim.approved_by,
        approved_at=claim.approved_at,
        approval_notes=claim.approval_notes,
        paid_at=claim.paid_at,
        payment_reference=claim.payment_reference,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        items=[]
    )


@router.get("/claims/{claim_id}", response_model=ReimbursementClaimResponse)
@require_permissions(["reimbursement:view"])
async def get_reimbursement_claim(
    request: Request,
    claim_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific reimbursement claim by ID."""
    
    claim = await claim_crud.get(db, claim_id)
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CLAIM_NOT_FOUND
        )
    
    # Get items
    items = await item_crud.get_by_fields(
        db,
        fields={"claim_id": claim.id}
    )
    
    item_responses = [
        ReimbursementItemResponse(
            id=item.id,
            category_id=item.category_id,
            expense_date=item.expense_date,
            description=item.description,
            amount=item.amount,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_amount=item.tax_amount,
            merchant_name=item.merchant_name,
            merchant_location=item.merchant_location,
            receipt_file_id=item.receipt_file_id,
            is_billable=item.is_billable,
            created_at=item.created_at
        )
        for item in items
    ]
    
    return ReimbursementClaimResponse(
        id=claim.id,
        claim_number=claim.claim_number,
        staff_id=claim.staff_id,
        project_id=claim.project_id,
        task_id=claim.task_id,
        claim_date=claim.claim_date,
        total_amount=claim.total_amount,
        currency=claim.currency,
        description=claim.description,
        status=claim.status,
        submitted_at=claim.submitted_at,
        approved_by=claim.approved_by,
        approved_at=claim.approved_at,
        approval_notes=claim.approval_notes,
        paid_at=claim.paid_at,
        payment_reference=claim.payment_reference,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        items=item_responses
    )


@router.post("/claims/{claim_id}/submit", response_model=ReimbursementClaimResponse)
@require_permissions(["reimbursement:create"])
async def submit_reimbursement_claim(
    request: Request,
    claim_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Submit a reimbursement claim for approval."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    claim = await claim_crud.get(db, claim_id)
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CLAIM_NOT_FOUND
        )
    
    if claim.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Claim already {claim.status}"
        )
    
    claim.status = "submitted"
    claim.submitted_at = datetime.now(timezone.utc)
    claim.updated_by = str(user_id) if user_id else None
    await db.flush()
    await db.commit()
    await db.refresh(claim)

    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':user_id,
            'title': f"Reimbursement claim {claim.claim_number} submitted",
            'message': f"Your reimbursement claim {claim.claim_number} has been submitted.",
            }
        )
    
    logger.info(f"Reimbursement claim submitted: {claim.id}")
    
    return ReimbursementClaimResponse(
        id=claim.id,
        claim_number=claim.claim_number,
        staff_id=claim.staff_id,
        project_id=claim.project_id,
        task_id=claim.task_id,
        claim_date=claim.claim_date,
        total_amount=claim.total_amount,
        currency=claim.currency,
        description=claim.description,
        status=claim.status,
        submitted_at=claim.submitted_at,
        approved_by=claim.approved_by,
        approved_at=claim.approved_at,
        approval_notes=claim.approval_notes,
        paid_at=claim.paid_at,
        payment_reference=claim.payment_reference,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        items=[]
    )

def _check_claim(claim):
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CLAIM_NOT_FOUND
        )
    
    if claim.status not in ["submitted", "draft"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Claim already {claim.status}"
        )

@router.post("/claims/{claim_id}/approve", response_model=ReimbursementClaimResponse)
@require_permissions(["reimbursement:approve"])
async def approve_reimbursement_claim(
    request: Request,
    claim_id: UUID,
    approval_data: ReimbursementClaimUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Approve or reject a reimbursement claim."""
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    claim = await claim_crud.get(db, claim_id)
    
    _check_claim(claim)
    
    claim.status = approval_data.status
    claim.approved_by = user_id
    claim.approved_at = datetime.now(timezone.utc)
    claim.approval_notes = approval_data.approval_notes
    claim.updated_by = str(user_id) if user_id else None
    items = await item_crud.get_by_fields(
        db,
        fields={"claim_id": claim.id}
    )

    for item in items:
        
        models = [
            (Project, item.project_id or claim.project_id),
            (Task, item.task_id or claim.task_id)
        ]

        for model, obj_id in models:
            if not obj_id:
                continue

            obj = await db.get(model, obj_id)
            if obj:
                obj.actual_cost = (obj.actual_cost or 0) + item.amount
            
    await db.flush()
    await db.commit()
    await db.refresh(claim)
    
    
    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':user_id,
            'title': f"Reimbursement claim {claim.claim_number} {claim.status}",
            'message': f"You have {claim.status} the reimbursement claim {claim.claim_number}.",
            }
        )
    staff = await get_staff(db, claim.staff_id, tenant_id)
    staff_by = await staff_crud.get_by_field(db, field="user_id", value=user_id)

    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(staff.user_id),
            'title': f"Reimbursement claim {claim.claim_number} {claim.status}",
            'message': f"Your reimbursement claim {claim.claim_number} has been {claim.status} by {staff_by.first_name} {staff_by.last_name}.",
            }
        )
    logger.info(f"Reimbursement claim {claim_id} {approval_data.status}")
    
    return ReimbursementClaimResponse(
        id=claim.id,
        claim_number=claim.claim_number,
        staff_id=claim.staff_id,
        project_id=claim.project_id,
        task_id=claim.task_id,
        claim_date=claim.claim_date,
        total_amount=claim.total_amount,
        currency=claim.currency,
        description=claim.description,
        status=claim.status,
        submitted_at=claim.submitted_at,
        approved_by=claim.approved_by,
        approved_at=claim.approved_at,
        approval_notes=claim.approval_notes,
        paid_at=claim.paid_at,
        payment_reference=claim.payment_reference,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        items=[]
    )


@router.post("/claims/{claim_id}/pay", response_model=ReimbursementClaimResponse)
@require_permissions(["reimbursement:paid"])
async def mark_reimbursement_paid(
    request: Request,
    claim_id: UUID,
    payment_reference: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Mark a reimbursement claim as paid."""
    
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)
    claim = await claim_crud.get(db, claim_id)
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CLAIM_NOT_FOUND
        )
    
    if claim.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Claim must be approved before payment"
        )
    
    claim.status = "paid"
    claim.paid_at = datetime.now(timezone.utc)
    claim.payment_reference = payment_reference
    claim.updated_by = str(user_id) if user_id else None
    await db.flush()
    await db.commit()
    await db.refresh(claim)
    
    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':user_id,
            'title': f"Reimbursement claim {claim.claim_number} {claim.status}",
            'message': f"You have {claim.status} the reimbursement claim {claim.claim_number}.",
            }
        )
    staff = await get_staff(db, claim.staff_id, tenant_id)
    staff_by = await staff_crud.get_by_field(db, field="user_id", value=user_id)

    await notify.create_notification(
        data={
            'tenant_id':str(tenant_id),
            'user_id':str(staff.user_id),
            'title': f"Reimbursement claim {claim.claim_number} {claim.status}",
            'message': f"Your reimbursement claim {claim.claim_number} has been {claim.status} by {staff_by.first_name} {staff_by.last_name}.",
            }
        )
    
    logger.info(f"Reimbursement claim paid: {claim.id}")
    
    return ReimbursementClaimResponse(
        id=claim.id,
        claim_number=claim.claim_number,
        staff_id=claim.staff_id,
        project_id=claim.project_id,
        task_id=claim.task_id,
        claim_date=claim.claim_date,
        total_amount=claim.total_amount,
        currency=claim.currency,
        description=claim.description,
        status=claim.status,
        submitted_at=claim.submitted_at,
        approved_by=claim.approved_by,
        approved_at=claim.approved_at,
        approval_notes=claim.approval_notes,
        paid_at=claim.paid_at,
        payment_reference=claim.payment_reference,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        items=[]
    )


# ============================================
# Expense Categories
# ============================================

@router.get("/categories", response_model=List[dict])
@require_permissions(["reimbursement:create"])
async def list_expense_categories(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """List all expense categories."""
    
    categories = await category_crud.get_multi(
        db,
        filters={"is_active": True}
    )
    
    return [
        {
            "id": str(cat.id),
            "name": cat.name,
            "code": cat.code,
            "description": cat.description,
            "requires_receipt": cat.requires_receipt,
            "max_amount": float(cat.max_amount) if cat.max_amount else None,
            "tax_deductible": cat.tax_deductible
        }
        for cat in categories
    ]


@router.delete("/claims/{claim_id}", response_model=SuccessResponse)
async def delete_reimbursement_claim(
    request: Request,
    claim_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a reimbursement claim (only allowed for draft claims)."""

    user_id = getattr(request.state, "user_id", None)

    claim = await claim_crud.get(db, claim_id)

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CLAIM_NOT_FOUND
        )

    # ERP rule: only draft claims can be deleted
    if claim.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft claims can be deleted"
        )

    # Soft delete items first
    await item_crud.delete_by_field(
        db,
        field="claim_id",
        value=claim_id,
        user_id=str(user_id) if user_id else None
    )

    # Soft delete claim
    await claim_crud.delete(
        db,
        id=claim_id,
        user_id=str(user_id) if user_id else None
    )

    await db.commit()

    logger.info(f"Reimbursement claim deleted: {claim_id}")

    return SuccessResponse(
        message="Reimbursement claim deleted successfully"
    )
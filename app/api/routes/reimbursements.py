"""
Reimbursement management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.api.schemas import (
    ReimbursementClaimCreate,
    ReimbursementClaimUpdate,
    ReimbursementClaimResponse,
    ReimbursementItemCreate,
    ReimbursementItemResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse
)
from app.db.models import ReimbursementClaim, ReimbursementItem, ExpenseCategory
from app.db.base import get_db_session
from app.services.crud import CRUDService
from app.events.publisher import EventType, publish_event
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/reimbursements", tags=["Reimbursement Management"])

claim_crud = CRUDService(ReimbursementClaim)
item_crud = CRUDService(ReimbursementItem)
category_crud = CRUDService(ExpenseCategory)


def generate_claim_number() -> str:
    """Generate a unique claim number."""
    return f"RMB-{datetime.now().strftime('%Y%m%d%H%M%S')}"


@router.get("/claims", response_model=PaginatedResponse)
async def list_reimbursement_claims(
    request: Request,
    pagination: PaginationParams = Depends(),
    staff_id: Optional[UUID] = None,
    status: Optional[str] = None,
    project_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """List reimbursement claims with filtering."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    filters = {}
    if staff_id:
        filters["staff_id"] = staff_id
    if status:
        filters["status"] = status
    if project_id:
        filters["project_id"] = project_id
    
    total = await claim_crud.count(db, tenant_id=tenant_id, filters=filters)
    
    claims = await claim_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        tenant_id=tenant_id,
        filters=filters
    )
    
    claim_responses = []
    for claim in claims:
        # Get items for this claim
        items = await item_crud.get_by_fields(
            db,
            fields={"claim_id": claim.id},
            tenant_id=tenant_id
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
            staff_name=None,  # TODO: Fetch staff name
            items=item_responses
        ))
    
    return PaginatedResponse.create(
        items=claim_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.post("/claims", response_model=ReimbursementClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_reimbursement_claim(
    request: Request,
    claim_data: ReimbursementClaimCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new reimbursement claim."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    # Calculate total from items
    total_amount = sum(
        item.amount for item in claim_data.items
    ) if claim_data.items else claim_data.total_amount
    
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
            "status": "draft"
        },
        tenant_id=tenant_id
    )
    
    # Create items
    for item_data in claim_data.items:
        await item_crud.create(
            db,
            obj_in={
                **item_data.model_dump(),
                "claim_id": claim.id
            },
            tenant_id=tenant_id
        )
    
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
async def get_reimbursement_claim(
    request: Request,
    claim_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific reimbursement claim by ID."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    claim = await claim_crud.get(db, claim_id, tenant_id=tenant_id)
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reimbursement claim not found"
        )
    
    # Get items
    items = await item_crud.get_by_fields(
        db,
        fields={"claim_id": claim.id},
        tenant_id=tenant_id
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
async def submit_reimbursement_claim(
    request: Request,
    claim_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Submit a reimbursement claim for approval."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    claim = await claim_crud.get(db, claim_id, tenant_id=tenant_id)
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reimbursement claim not found"
        )
    
    if claim.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Claim already {claim.status}"
        )
    
    claim.status = "submitted"
    claim.submitted_at = datetime.utcnow()
    await db.flush()
    
    # Publish event
    await publish_event(
        event_type=EventType.REIMBURSEMENT_SUBMITTED,
        aggregate_type="reimbursement",
        aggregate_id=str(claim.id),
        tenant_id=tenant_id,
        payload={
            "claim_number": claim.claim_number,
            "staff_id": str(claim.staff_id),
            "total_amount": float(claim.total_amount),
            "currency": claim.currency
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


@router.post("/claims/{claim_id}/approve", response_model=ReimbursementClaimResponse)
async def approve_reimbursement_claim(
    request: Request,
    claim_id: UUID,
    approval_data: ReimbursementClaimUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Approve or reject a reimbursement claim."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    claim = await claim_crud.get(db, claim_id, tenant_id=tenant_id)
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reimbursement claim not found"
        )
    
    if claim.status not in ["submitted", "draft"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Claim already {claim.status}"
        )
    
    claim.status = approval_data.status
    claim.approved_by = user_id
    claim.approved_at = datetime.utcnow()
    claim.approval_notes = approval_data.approval_notes
    
    await db.flush()
    
    # Publish event
    if approval_data.status == "approved":
        await publish_event(
            event_type=EventType.REIMBURSEMENT_APPROVED,
            aggregate_type="reimbursement",
            aggregate_id=str(claim.id),
            tenant_id=tenant_id,
            payload={
                "claim_number": claim.claim_number,
                "staff_id": str(claim.staff_id),
                "approved_by": user_id,
                "amount": float(claim.total_amount)
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
async def mark_reimbursement_paid(
    request: Request,
    claim_id: UUID,
    payment_reference: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Mark a reimbursement claim as paid."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    claim = await claim_crud.get(db, claim_id, tenant_id=tenant_id)
    
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reimbursement claim not found"
        )
    
    if claim.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Claim must be approved before payment"
        )
    
    claim.status = "paid"
    claim.paid_at = datetime.utcnow()
    claim.payment_reference = payment_reference
    
    await db.flush()
    
    # Publish event
    await publish_event(
        event_type=EventType.REIMBURSEMENT_PAID,
        aggregate_type="reimbursement",
        aggregate_id=str(claim.id),
        tenant_id=tenant_id,
        payload={
            "claim_number": claim.claim_number,
            "staff_id": str(claim.staff_id),
            "amount": float(claim.total_amount),
            "payment_reference": payment_reference
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
async def list_expense_categories(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    """List all expense categories."""
    tenant_id = getattr(request.state, 'tenant_id', None)
    
    categories = await category_crud.get_multi(
        db,
        tenant_id=tenant_id,
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

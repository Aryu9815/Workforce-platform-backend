from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.db.base import get_db_session
from app.schemas import (
    TaskLabelCreate,
    TaskLabelUpdate,
    TaskLabelResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse
)

from app.services.crud import task_label_crud
from app.utils.rbac_middleware import require_permissions


router = APIRouter(prefix="/task-labels", tags=["Task Labels"])


@router.post(
    "",
    response_model=TaskLabelResponse,
    status_code=status.HTTP_201_CREATED
)
@require_permissions(["task_label:create"])
async def create_task_label(
    request: Request,
    data: TaskLabelCreate,
    db: AsyncSession = Depends(get_db_session)
):

    user_id = getattr(request.state, "user_id", None)

    label = await task_label_crud.create(
        db,
        obj_in=data.model_dump(),
        user_id=user_id
    )

    return label

@router.get("", response_model=PaginatedResponse)
@require_permissions(["task_label:view"])
async def list_task_labels(
    request: Request,
    pagination: PaginationParams = Depends(),
    project_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db_session)
):

    filters = {}

    if project_id:
        filters["project_id"] = project_id

    total = await task_label_crud.count(db, filters=filters)

    labels = await task_label_crud.get_multi(
        db,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=filters
    )

    label_responses = [
        TaskLabelResponse.model_validate(label)
        for label in labels
    ]


    return PaginatedResponse.create(
        items=label_responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )
@router.get("/project/{project_id}",response_model=List[TaskLabelResponse])
@require_permissions(["task_label:view"])
async def list_task_labels_by_project(
    request: Request,
    project_id: UUID = None,
    db: AsyncSession = Depends(get_db_session)
):

    labels = await task_label_crud.get_by_fields(
        db,
        fields={"project_id": project_id},
    )

    return labels

@router.get("/{label_id}", response_model=TaskLabelResponse)
@require_permissions(["task_label:view"])
async def get_task_label(
    request: Request,
    label_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):

    label = await task_label_crud.get(db, label_id)

    return label




@router.put("/{label_id}", response_model=TaskLabelResponse)
@require_permissions(["task_label:update"])
async def update_task_label(
    request: Request,
    label_id: UUID,
    data: TaskLabelUpdate,
    db: AsyncSession = Depends(get_db_session)
):

    user_id = getattr(request.state, "user_id", None)

    label = await task_label_crud.get(db, label_id)

    updated_label = await task_label_crud.update(
        db,
        db_obj=label,
        obj_in=data.model_dump(exclude_unset=True),
        updated_by=user_id
    )

    return updated_label
@router.delete("/{label_id}", response_model=SuccessResponse)
@require_permissions(["task_label:delete"])
async def delete_task_label(
    request: Request,
    label_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):

    user_id = getattr(request.state, "user_id", None)

    await task_label_crud.delete(
        db,
        id=label_id,
        user_id=user_id
    )

    return SuccessResponse(message="Task label deleted successfully")
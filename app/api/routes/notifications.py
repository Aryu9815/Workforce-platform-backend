from fastapi import APIRouter, HTTPException, status, Request
from app.core.logging_config import get_logger
from typing import List
from app.schemas import NotificationResponse
from app.services import notify

logger = get_logger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notification Management"])

@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    request: Request,
):
    user_id = getattr(request.state, 'user_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)
    return await notify.get_notifications(user_id, tenant_id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    request: Request,
    notification_id: str,
):
    user_id = getattr(request.state, 'user_id', None)
    notification = await notify.mark_notification_as_read(notification_id, user_id)
    return notification

@router.post("/push/subscribe")
async def subscribe_push_notifications(
    request: Request,
    subscription_data: dict,
):
    user_id = getattr(request.state, 'common_id', None)
    tenant_id = getattr(request.state, 'tenant_id', None)

    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    await notify.push_subscribe(user_id, tenant_id, subscription_data)

    return {"message": "Push subscription successful"}
from pywebpush import webpush
import json
from app.core.config import settings

PUBLIC_KEY = settings.VAPID_PUBLIC_KEY
PRIVATE_KEY = settings.VAPID_PRIVATE_KEY
EMAIL = settings.VAPID_EMAIL

async def send_push(subscription, data: dict):
    webpush(
        subscription_info={
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh,
                "auth": subscription.auth,
            },
        },
        data=json.dumps(data),
        vapid_private_key=PRIVATE_KEY,
        vapid_claims={"sub": EMAIL}
    )
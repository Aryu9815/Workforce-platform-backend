from email.message import EmailMessage
import aiosmtplib
from app.core.logging_config import get_logger
from app.core.config import settings
logger = get_logger("email")

SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USERNAME = settings.SMTP_USER
SMTP_PASSWORD = settings.SMTP_PASSWORD

async def send_email(payload: dict):
    """
    params:
    payload: (dict){
        "to": "user@example.com",
        "subject": "Hello",
        "body": "Welcome...",
        "html": "<p>Welcome</p>"   # optional
    }
    """
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_USERNAME
        msg["To"] = payload["to"]
        msg["Subject"] = payload["subject"]

        if "html" in payload:
            msg.add_alternative(payload["html"], subtype="html")
        else:
            msg.set_content(payload["body"])

        logger.info(f"Sending email to: {payload['to']}")

        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=True,
        )

        logger.info(f"Email sent to {payload['to']}")
        return True

    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}")
        return False
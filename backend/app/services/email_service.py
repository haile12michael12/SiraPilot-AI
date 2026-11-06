import smtplib
from email.message import EmailMessage

import structlog

from app.core.config import Settings

logger = structlog.get_logger(__name__)


def send_email(settings: Settings, recipient: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.warning("email_delivery_disabled", recipient_domain=recipient.rsplit("@", 1)[-1])
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        if settings.smtp_username:
            password = settings.smtp_password.get_secret_value() if settings.smtp_password else ""
            server.login(settings.smtp_username, password)
        server.send_message(message)
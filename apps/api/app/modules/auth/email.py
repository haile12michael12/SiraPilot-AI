"""SMTP delivery for verification and password-recovery messages."""

import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from app.infra.postgres.config import AuthSettings


class EmailDeliveryError(RuntimeError):
    """Raised when a configured SMTP server cannot accept an auth message."""


def send_auth_email(
    settings: AuthSettings,
    *,
    recipient: str,
    purpose: str,
    token: str,
) -> None:
    if settings.public_base_url is None or settings.email_from is None or settings.smtp_host is None:
        raise RuntimeError("Authentication email settings are incomplete")

    action = "verify-email" if purpose == "verification" else "password-reset"
    url = f"{settings.public_base_url.rstrip('/')}/api/v1/auth/{action}#{quote(token)}"
    message = EmailMessage()
    message["Subject"] = (
        "Verify your SiraPilot account"
        if purpose == "verification"
        else "Reset your SiraPilot password"
    )
    message["From"] = str(settings.email_from)
    message["To"] = recipient
    message.set_content(
        f"Use this link to {('verify your email address' if purpose == 'verification' else 'reset your password')}:\n\n"
        f"{url}\n\n"
        "If you did not request this, you can ignore this message."
    )

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
                context=ssl.create_default_context(),
            ) as server:
                _deliver(server, settings, message)
        else:
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
            ) as server:
                server.ehlo()
                if settings.smtp_starttls:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                _deliver(server, settings, message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Authentication email could not be delivered") from exc


def _deliver(server: smtplib.SMTP, settings: AuthSettings, message: EmailMessage) -> None:
    if settings.smtp_username is not None and settings.smtp_password is not None:
        server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
    refused = server.send_message(message)
    if refused:
        raise EmailDeliveryError("Authentication email was refused by the SMTP server")

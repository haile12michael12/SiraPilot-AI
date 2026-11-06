from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password, hash_token
from app.models import (
    CareerProfile,
    EmailVerificationToken,
    PasswordResetToken,
    RefreshSession,
    User,
)
from app.services.token_service import create_email_token, token_is_expired, utc_now


def register_user(session: Session, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    if session.scalar(select(User.id).where(User.email == normalized_email)):
        raise ValueError("email_exists")
    user = User(email=normalized_email, password_hash=hash_password(password))
    session.add(user)
    session.flush()
    session.add(CareerProfile(user_id=user.id))
    session.flush()
    return user


def create_verification_token(session: Session, user: User, settings: Settings) -> str:
    return create_email_token(
        session,
        EmailVerificationToken,
        user.id,
        timedelta(hours=settings.auth_email_verification_hours),
    )


def verify_email(session: Session, raw_token: str) -> bool:
    token = session.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == hash_token(raw_token),
            EmailVerificationToken.used_at.is_(None),
        )
    )
    if token is None or token_is_expired(token.expires_at):
        return False
    user = session.get(User, token.user_id)
    if user is None:
        return False
    token.used_at = utc_now()
    user.is_email_verified = True
    session.commit()
    return True


def create_password_reset_token(
    session: Session,
    user: User,
    settings: Settings,
) -> str:
    return create_email_token(
        session,
        PasswordResetToken,
        user.id,
        timedelta(minutes=settings.auth_password_reset_minutes),
    )


def reset_password(session: Session, raw_token: str, password: str) -> bool:
    token = session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(raw_token),
            PasswordResetToken.used_at.is_(None),
        )
    )
    if token is None or token_is_expired(token.expires_at):
        return False
    user = session.get(User, token.user_id)
    if user is None:
        return False
    now = utc_now()
    token.used_at = now
    user.password_hash = hash_password(password)
    session.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    session.commit()
    return True
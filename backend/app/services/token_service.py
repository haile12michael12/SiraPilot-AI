from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_opaque_token, hash_token
from app.models import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshSession,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def token_is_expired(value: datetime, now: datetime | None = None) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value <= (now or utc_now())


def create_refresh_session(
    session: Session,
    user_id: UUID,
    settings: Settings,
    family_id: UUID | None = None,
) -> tuple[RefreshSession, str]:
    raw_token = create_opaque_token()
    refresh_session = RefreshSession(
        user_id=user_id,
        family_id=family_id or uuid4(),
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(days=settings.auth_refresh_token_days),
    )
    session.add(refresh_session)
    session.flush()
    return refresh_session, raw_token


def rotate_refresh_session(
    session: Session,
    raw_token: str,
    settings: Settings,
) -> tuple[RefreshSession, str] | None:
    current = session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_token))
    )
    if current is None:
        return None

    now = utc_now()
    if current.revoked_at is not None:
        session.execute(
            update(RefreshSession)
            .where(
                RefreshSession.family_id == current.family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        session.commit()
        return None
    if token_is_expired(current.expires_at, now):
        current.revoked_at = now
        session.commit()
        return None

    replacement, replacement_token = create_refresh_session(
        session, current.user_id, settings, current.family_id
    )
    result = session.execute(
        update(RefreshSession)
        .where(
            RefreshSession.id == current.id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=now, replaced_by_id=replacement.id)
    )
    if result.rowcount != 1:
        session.rollback()
        return None
    session.commit()
    return replacement, replacement_token


def revoke_refresh_family(session: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    current = session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw_token))
    )
    if current is None:
        return
    session.execute(
        update(RefreshSession)
        .where(
            RefreshSession.family_id == current.family_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=utc_now())
    )
    session.commit()


def create_email_token(
    session: Session,
    model: type[EmailVerificationToken] | type[PasswordResetToken],
    user_id: UUID,
    lifetime: timedelta,
) -> str:
    now = utc_now()
    session.execute(
        update(model)
        .where(model.user_id == user_id, model.used_at.is_(None))
        .values(used_at=now)
    )
    raw_token = create_opaque_token()
    session.add(
        model(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=now + lifetime,
        )
    )
    return raw_token
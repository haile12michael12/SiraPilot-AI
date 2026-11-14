"""Persistence operations for PostgreSQL-backed authentication."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import case, delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.infra.postgres.models import Account
from app.modules.auth.models import AuthRateLimit, AuthSession, AuthToken, User


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock_email(self, email: str) -> None:
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))"), {"email": email}
        )

    def user_by_email(self, email: str, *, lock: bool = False) -> User | None:
        statement = select(User).where(User.email == email)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def user_by_id(self, user_id: UUID, *, lock: bool = False) -> User | None:
        statement = select(User).where(User.id == user_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def create_user(self, *, email: str, password_hash: str) -> User:
        account = Account(id=uuid4())
        user = User(
            id=uuid4(),
            account_id=account.id,
            email=email,
            password_hash=password_hash,
        )
        self._session.add_all([account, user])
        self._session.flush()
        return user

    def create_token(
        self,
        *,
        user_id: UUID,
        purpose: str,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        self._session.execute(
            delete(AuthToken).where(AuthToken.expires_at < now - timedelta(days=30))
        )
        self._session.execute(
            update(AuthToken)
            .where(
                AuthToken.user_id == user_id,
                AuthToken.purpose == purpose,
                AuthToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        self._session.add(
            AuthToken(
                id=uuid4(),
                user_id=user_id,
                purpose=purpose,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        self._session.flush()

    def valid_token(self, *, purpose: str, token_hash: str, now: datetime) -> tuple[AuthToken, User] | None:
        result = self._session.execute(
            select(AuthToken, User)
            .join(User, User.id == AuthToken.user_id)
            .where(
                AuthToken.purpose == purpose,
                AuthToken.token_hash == token_hash,
                AuthToken.consumed_at.is_(None),
                AuthToken.expires_at > now,
            )
            .with_for_update(of=AuthToken)
        ).one_or_none()
        return (result[0], result[1]) if result is not None else None

    def consume_token(self, token: AuthToken, now: datetime) -> None:
        token.consumed_at = now

    def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> AuthSession:
        self._session.execute(
            delete(AuthSession).where(
                (AuthSession.revoked_at < now - timedelta(days=30))
                | (AuthSession.expires_at < now - timedelta(days=30))
            )
        )
        auth_session = AuthSession(
            id=uuid4(), user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self._session.add(auth_session)
        self._session.flush()
        return auth_session

    def get_active_session(self, token_hash: str, now: datetime) -> tuple[AuthSession, User] | None:
        result = self._session.execute(
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
        ).one_or_none()
        return (result[0], result[1]) if result is not None else None

    def revoke_session(self, session_id: UUID, now: datetime) -> None:
        self._session.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def revoke_user_sessions(self, user_id: UUID, now: datetime) -> None:
        self._session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def consume_rate_limit(
        self,
        *,
        bucket_hash: str,
        now: datetime,
        window: timedelta,
    ) -> int:
        expired_before = now - window
        self._session.execute(
            delete(AuthRateLimit).where(AuthRateLimit.window_started_at < now - timedelta(days=1))
        )
        statement = insert(AuthRateLimit).values(
            bucket_hash=bucket_hash,
            window_started_at=now,
            attempts=1,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[AuthRateLimit.bucket_hash],
            set_={
                "window_started_at": case(
                    (AuthRateLimit.window_started_at <= expired_before, now),
                    else_=AuthRateLimit.window_started_at,
                ),
                "attempts": case(
                    (AuthRateLimit.window_started_at <= expired_before, 1),
                    else_=AuthRateLimit.attempts + 1,
                ),
            },
        ).returning(AuthRateLimit.attempts)
        return int(self._session.scalar(statement))

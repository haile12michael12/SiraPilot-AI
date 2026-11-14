"""Authentication workflows over the isolated PostgreSQL target."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy.orm import Session

from app.infra.postgres.config import AuthSettings
from app.infra.postgres.sessions import PostgresDatabase
from app.modules.auth.repository import AuthRepository
from app.shared.timeutil import utc_now

PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65_536, parallelism=2)
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))


@dataclass(frozen=True)
class AuthEmail:
    purpose: str
    recipient: str
    token: str


@dataclass(frozen=True)
class LoginResult:
    account_id: UUID
    email: str
    token: str
    expires_in: int


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _rate_hash(settings: AuthSettings, action: str, value: str) -> str:
    if settings.rate_limit_secret is None:
        raise RuntimeError("AUTH_RATE_LIMIT_SECRET must be configured")
    key = settings.rate_limit_secret.get_secret_value().encode()
    payload = f"{action}:{value}".encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _consume_limits(
    session: Session,
    settings: AuthSettings,
    *,
    now: datetime,
    action: str,
    email: str | None,
    client_ip: str,
    attempts: int,
    window_seconds: int,
    email_attempts: int | None = None,
) -> bool:
    repository = AuthRepository(session)
    buckets = [(f"{action}:ip", client_ip, attempts)]
    if email is not None:
        buckets.append((f"{action}:email", email, email_attempts or attempts))
    allowed = True
    for scope, value, maximum in buckets:
        current = repository.consume_rate_limit(
            bucket_hash=_rate_hash(settings, scope, value),
            now=now,
            window=timedelta(seconds=window_seconds),
        )
        allowed = allowed and current <= maximum
    return allowed


def register(
    database: PostgresDatabase,
    settings: AuthSettings,
    *,
    email: str,
    password: str,
    client_ip: str,
) -> tuple[AuthEmail | None, bool]:
    now = utc_now()
    email = email.casefold()
    with database.transaction() as session:
        allowed = _consume_limits(
            session,
            settings,
            now=now,
            action="register",
            email=email,
            client_ip=client_ip,
            attempts=10,
            email_attempts=3,
            window_seconds=3600,
        )
    if not allowed:
        return None, True

    password_hash = PASSWORD_HASHER.hash(password)
    raw_token = secrets.token_urlsafe(32)
    with database.transaction() as session:
        repository = AuthRepository(session)
        repository.lock_email(email)
        if repository.user_by_email(email) is not None:
            return None, False
        user = repository.create_user(email=email, password_hash=password_hash)
        repository.create_token(
            user_id=user.id,
            purpose="verification",
            token_hash=token_digest(raw_token),
            expires_at=now + timedelta(seconds=settings.verification_ttl_seconds),
            now=now,
        )
    return AuthEmail("verification", email, raw_token), False


def request_verification(
    database: PostgresDatabase,
    settings: AuthSettings,
    *,
    email: str,
    client_ip: str,
) -> tuple[AuthEmail | None, bool]:
    now = utc_now()
    email = email.casefold()
    with database.transaction() as session:
        allowed = _consume_limits(
            session,
            settings,
            now=now,
            action="verification",
            email=email,
            client_ip=client_ip,
            attempts=10,
            email_attempts=3,
            window_seconds=3600,
        )
        if not allowed:
            return None, True
        repository = AuthRepository(session)
        user = repository.user_by_email(email, lock=True)
        if user is None or user.email_verified_at is not None:
            return None, False
        raw_token = secrets.token_urlsafe(32)
        repository.create_token(
            user_id=user.id,
            purpose="verification",
            token_hash=token_digest(raw_token),
            expires_at=now + timedelta(seconds=settings.verification_ttl_seconds),
            now=now,
        )
    return AuthEmail("verification", email, raw_token), False


def verify_email(database: PostgresDatabase, token: str) -> bool:
    now = utc_now()
    with database.transaction() as session:
        repository = AuthRepository(session)
        result = repository.valid_token(
            purpose="verification", token_hash=token_digest(token), now=now
        )
        if result is None:
            return False
        auth_token, user = result
        user.email_verified_at = now
        repository.consume_token(auth_token, now)
        return True


def login(
    database: PostgresDatabase,
    settings: AuthSettings,
    *,
    email: str,
    password: str,
    client_ip: str,
) -> tuple[LoginResult | None, bool]:
    now = utc_now()
    email = email.casefold()
    with database.transaction() as session:
        allowed = _consume_limits(
            session,
            settings,
            now=now,
            action="login",
            email=email,
            client_ip=client_ip,
            attempts=20,
            email_attempts=10,
            window_seconds=900,
        )
    if not allowed:
        return None, True

    with database.session() as session:
        user = AuthRepository(session).user_by_email(email)
        stored_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_matches = _verify_password(stored_hash, password)
        if (
            user is None
            or user.email_verified_at is None
            or not password_matches
        ):
            return None, False
        user_id, account_id, encoded_email = user.id, user.account_id, user.email
        needs_rehash = PASSWORD_HASHER.check_needs_rehash(stored_hash)

    raw_token = secrets.token_urlsafe(32)
    with database.transaction() as session:
        repository = AuthRepository(session)
        current_user = repository.user_by_id(user_id, lock=True)
        if (
            current_user is None
            or current_user.email_verified_at is None
            or current_user.password_hash != stored_hash
        ):
            return None, False
        if needs_rehash:
            current_user.password_hash = PASSWORD_HASHER.hash(password)
        repository.create_session(
            user_id=user_id,
            token_hash=token_digest(raw_token),
            expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
            now=now,
        )
    return (
        LoginResult(
            account_id=account_id,
            email=encoded_email,
            token=raw_token,
            expires_in=settings.session_ttl_seconds,
        ),
        False,
    )


def _verify_password(encoded_hash: str, password: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(encoded_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def request_password_reset(
    database: PostgresDatabase,
    settings: AuthSettings,
    *,
    email: str,
    client_ip: str,
) -> tuple[AuthEmail | None, bool]:
    now = utc_now()
    email = email.casefold()
    with database.transaction() as session:
        allowed = _consume_limits(
            session,
            settings,
            now=now,
            action="password-reset",
            email=email,
            client_ip=client_ip,
            attempts=10,
            email_attempts=3,
            window_seconds=3600,
        )
        if not allowed:
            return None, True
        repository = AuthRepository(session)
        user = repository.user_by_email(email, lock=True)
        if user is None or user.email_verified_at is None:
            return None, False
        raw_token = secrets.token_urlsafe(32)
        repository.create_token(
            user_id=user.id,
            purpose="password_reset",
            token_hash=token_digest(raw_token),
            expires_at=now + timedelta(seconds=settings.password_reset_ttl_seconds),
            now=now,
        )
    return AuthEmail("password_reset", email, raw_token), False


def reset_password(
    database: PostgresDatabase,
    settings: AuthSettings,
    *,
    token: str,
    password: str,
    client_ip: str,
) -> tuple[bool, bool]:
    now = utc_now()
    with database.transaction() as session:
        allowed = _consume_limits(
            session,
            settings,
            now=now,
            action="password-reset-submit",
            email=None,
            client_ip=client_ip,
            attempts=10,
            window_seconds=900,
        )
    if not allowed:
        return False, True

    digest = token_digest(token)
    with database.session() as session:
        result = AuthRepository(session).valid_token(
            purpose="password_reset", token_hash=digest, now=now
        )
        if result is None:
            return False, False
        user_id = result[1].id
    password_hash = PASSWORD_HASHER.hash(password)
    with database.transaction() as session:
        repository = AuthRepository(session)
        result = repository.valid_token(purpose="password_reset", token_hash=digest, now=now)
        user = repository.user_by_id(user_id, lock=True)
        if result is None or user is None or result[1].id != user_id:
            return False, False
        auth_token, _ = result
        user.password_hash = password_hash
        repository.consume_token(auth_token, now)
        repository.revoke_user_sessions(user_id, now)
    return True, False


def logout(database: PostgresDatabase, session_id: UUID) -> None:
    with database.transaction() as session:
        AuthRepository(session).revoke_session(session_id, utc_now())

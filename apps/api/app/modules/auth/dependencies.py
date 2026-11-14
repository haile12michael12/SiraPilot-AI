"""Authentication dependencies for the opt-in PostgreSQL target."""

from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.infra.postgres.config import AuthSettings
from app.infra.postgres.sessions import PostgresDatabase
from app.modules.auth.models import AuthSession, User


def get_postgres_database(request: Request) -> PostgresDatabase:
    database = cast(PostgresDatabase | None, request.app.state.postgres_database)
    if database is None:
        raise HTTPException(503, "PostgreSQL authentication is not configured.")
    return database


def get_auth_settings(request: Request) -> AuthSettings:
    return cast(AuthSettings, request.app.state.auth_settings)


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


DatabaseDep = Annotated[PostgresDatabase, Depends(get_postgres_database)]
AuthSettingsDep = Annotated[AuthSettings, Depends(get_auth_settings)]
AppSettingsDep = Annotated[Settings, Depends(get_app_settings)]


def resolve_session(
    request: Request,
    database: DatabaseDep,
) -> tuple[Session, AuthSession, User]:
    token = request.cookies.get("__Host-sirapilot_session")
    authorization = request.headers.get("authorization", "")
    if token is None and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(401, "Authentication required.")

    from app.modules.auth.repository import AuthRepository
    from app.modules.auth.service import token_digest
    from app.shared.timeutil import utc_now

    with database.session() as session:
        result = AuthRepository(session).get_active_session(token_digest(token), utc_now())
        if result is None:
            raise HTTPException(401, "Authentication required.")
        auth_session, user = result
        if user.email_verified_at is None:
            raise HTTPException(401, "Authentication required.")
        session.expunge(auth_session)
        session.expunge(user)
        return session, auth_session, user


def get_current_identity(
    identity: Annotated[tuple[Session, AuthSession, User], Depends(resolve_session)],
) -> tuple[AuthSession, User]:
    _, auth_session, user = identity
    return auth_session, user


CurrentIdentityDep = Annotated[tuple[AuthSession, User], Depends(get_current_identity)]

from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, is_valid_csrf_token
from app.models import RefreshSession, User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_db(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def require_csrf(request: Request) -> None:
    if not is_valid_csrf_token(
        request.cookies.get("csrf_token"),
        request.headers.get("X-CSRF-Token"),
        request.app.state.settings,
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request could not be verified")


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    session: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    try:
        claims = decode_access_token(token, request.app.state.settings)
        user_id = UUID(claims["sub"])
        session_id = UUID(claims["sid"])
        if claims["type"] != "access":
            raise InvalidTokenError("wrong token type")
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    refresh_session = session.get(RefreshSession, session_id)
    user = session.get(User, user_id)
    if (
        refresh_session is None
        or refresh_session.user_id != user_id
        or refresh_session.revoked_at is not None
        or user is None
        or not user.is_active
    ):
        raise unauthorized
    return user
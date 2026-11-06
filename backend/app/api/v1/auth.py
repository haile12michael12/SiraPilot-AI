from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_csrf
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token,
    create_csrf_token,
    hash_password,
    needs_password_rehash,
    verify_password,
)
from app.models import User
from app.schemas.auth import (
    AuthResponse,
    EmailRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenRequest,
    UserResponse,
)
from app.services.auth_service import (
    create_password_reset_token,
    create_verification_token,
    register_user,
    reset_password,
    verify_email,
)
from app.services.email_service import send_email
from app.services.token_service import (
    create_refresh_session,
    revoke_refresh_family,
    rotate_refresh_session,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
AUTH_FAILURE = "Invalid email or password"


def _set_csrf_cookie(response: Response, request: Request) -> None:
    settings = request.app.state.settings
    token = create_csrf_token(settings)
    response.set_cookie(
        "csrf_token",
        token,
        max_age=12 * 60 * 60,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def _set_refresh_cookie(response: Response, request: Request, token: str) -> None:
    settings = request.app.state.settings
    response.set_cookie(
        "refresh_token",
        token,
        max_age=settings.auth_refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/api/v1/auth",
    )


def _clear_auth_cookies(response: Response, request: Request) -> None:
    settings = request.app.state.settings
    response.delete_cookie(
        "refresh_token",
        path="/api/v1/auth",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        "csrf_token",
        path="/",
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _queue_email(
    background_tasks: BackgroundTasks,
    request: Request,
    recipient: str,
    subject: str,
    link: str,
) -> None:
    background_tasks.add_task(
        send_email,
        request.app.state.settings,
        recipient,
        subject,
        f"Use this link to continue: {link}\n\nIf you did not request this, you can ignore this message.",
    )


@router.get("/csrf", summary="Issue a signed CSRF token")
def issue_csrf_token(request: Request, response: Response) -> dict[str, str]:
    if not request.cookies.get("csrf_token"):
        _set_csrf_cookie(response, request)
    return {"message": "CSRF token ready"}


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf), Depends(rate_limit("register", 5))],
)
def register(
    payload: RegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> MessageResponse:
    try:
        user = register_user(session, str(payload.email), payload.password)
        raw_token = create_verification_token(session, user, request.app.state.settings)
        session.commit()
    except (ValueError, IntegrityError):
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Unable to register with these details",
        ) from None

    link = f"{request.app.state.settings.frontend_url}/verify-email?token={raw_token}"
    _queue_email(background_tasks, request, user.email, "Verify your SiraPilot account", link)
    return MessageResponse(message="Registration received. Check your email to verify your account.")


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(require_csrf), Depends(rate_limit("login", 5))],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> AuthResponse:
    email = str(payload.email).strip().lower()
    user = session.scalar(select(User).where(User.email == email))
    valid_password = verify_password(
        payload.password,
        user.password_hash if user is not None else None,
    )
    if user is None or not valid_password or not user.is_active or not user.is_email_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, AUTH_FAILURE)

    if needs_password_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    refresh_session, refresh_token = create_refresh_session(
        session, user.id, request.app.state.settings
    )
    session.commit()
    access_token, expires_in = create_access_token(
        str(user.id), str(refresh_session.id), request.app.state.settings
    )
    _set_refresh_cookie(response, request, refresh_token)
    _set_csrf_cookie(response, request)
    return AuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=AuthResponse,
    dependencies=[Depends(require_csrf), Depends(rate_limit("refresh", 10))],
)
def refresh(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> AuthResponse:
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    rotated = rotate_refresh_session(session, raw_token, request.app.state.settings)
    if rotated is None:
        _clear_auth_cookies(response, request)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    refresh_session, next_token = rotated
    user = session.get(User, refresh_session.user_id)
    if user is None or not user.is_active:
        revoke_refresh_family(session, next_token)
        _clear_auth_cookies(response, request)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    access_token, expires_in = create_access_token(
        str(user.id), str(refresh_session.id), request.app.state.settings
    )
    _set_refresh_cookie(response, request, next_token)
    _set_csrf_cookie(response, request)
    return AuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf), Depends(rate_limit("logout", 20))],
)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_db),
) -> Response:
    revoke_refresh_family(session, request.cookies.get("refresh_token"))
    _clear_auth_cookies(response, request)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    dependencies=[Depends(require_csrf), Depends(rate_limit("verify-email", 10))],
)
def verify_email_address(
    payload: TokenRequest,
    session: Session = Depends(get_db),
) -> MessageResponse:
    if not verify_email(session, payload.token):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verification link is invalid or expired")
    return MessageResponse(message="Email verified. You can now sign in.")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    dependencies=[Depends(require_csrf), Depends(rate_limit("resend-verification", 5))],
)
def resend_verification(
    payload: EmailRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> MessageResponse:
    user = session.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is not None and not user.is_email_verified and user.is_active:
        token = create_verification_token(session, user, request.app.state.settings)
        session.commit()
        link = f"{request.app.state.settings.frontend_url}/verify-email?token={token}"
        _queue_email(background_tasks, request, user.email, "Verify your SiraPilot account", link)
    return MessageResponse(message="If the account needs verification, an email will be sent.")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(require_csrf), Depends(rate_limit("forgot-password", 5))],
)
def forgot_password(
    payload: EmailRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> MessageResponse:
    user = session.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is not None and user.is_active:
        token = create_password_reset_token(session, user, request.app.state.settings)
        session.commit()
        link = f"{request.app.state.settings.frontend_url}/reset-password?token={token}"
        _queue_email(background_tasks, request, user.email, "Reset your SiraPilot password", link)
    return MessageResponse(message="If the account exists, password reset instructions will be sent.")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(require_csrf), Depends(rate_limit("reset-password", 5))],
)
def reset_password_endpoint(
    payload: ResetPasswordRequest,
    session: Session = Depends(get_db),
) -> MessageResponse:
    if not reset_password(session, payload.token, payload.password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reset link is invalid or expired")
    return MessageResponse(message="Password updated. Sign in with your new password.")
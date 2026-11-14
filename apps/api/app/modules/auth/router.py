"""Public PostgreSQL authentication endpoints."""

import logging
import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import Settings
from app.infra.postgres.config import AuthSettings
from app.modules.auth.dependencies import (
    AppSettingsDep,
    AuthSettingsDep,
    CurrentIdentityDep,
    DatabaseDep,
)
from app.modules.auth.email import EmailDeliveryError, send_auth_email
from app.modules.auth.models import AuthSession, User
from app.modules.auth.schemas import (
    Accepted,
    AuthenticatedUser,
    LoginRequest,
    LoginResponse,
    PasswordReset,
    PasswordUpdated,
    Registration,
    TokenRequest,
    VerificationRequest,
    Verified,
)
from app.modules.auth.service import (
    AuthEmail,
    login as authenticate,
    logout as revoke_session,
    register as create_account,
    request_password_reset,
    request_verification,
    reset_password,
    verify_email,
)

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "__Host-sirapilot_session"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _require_allowed_origin(
    request: Request,
    auth_settings: AuthSettings,
    app_settings: Settings,
) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        return
    configured_origin = ""
    if auth_settings.public_base_url is not None:
        parsed = urlsplit(auth_settings.public_base_url)
        configured_origin = f"{parsed.scheme}://{parsed.netloc}"
    allowed = {
        app_settings.web_dev_origin.rstrip("/"),
        f"chrome-extension://{app_settings.extension_id}",
        configured_origin,
    }
    if origin not in allowed:
        raise HTTPException(403, "Origin is not allowed.")


def _require_rate_limit_not_exceeded(limited: bool) -> None:
    if limited:
        raise HTTPException(429, "Too many authentication attempts.", headers={"Retry-After": "900"})


def _schedule_email(
    background_tasks: BackgroundTasks,
    settings: AuthSettings,
    message: AuthEmail | None,
) -> None:
    if message is not None:
        background_tasks.add_task(
            _send_email_safely,
            settings,
            recipient=message.recipient,
            purpose=message.purpose,
            token=message.token,
        )


def _send_email_safely(
    settings: AuthSettings,
    *,
    recipient: str,
    purpose: str,
    token: str,
) -> None:
    try:
        send_auth_email(settings, recipient=recipient, purpose=purpose, token=token)
    except EmailDeliveryError:
        logger.error(
            "authentication email delivery failed",
            extra={"event": "auth.email_delivery_failed", "purpose": purpose},
        )


def _auth_page(content: str) -> HTMLResponse:
    nonce = secrets.token_urlsafe(18)
    html = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>SiraPilot account</title></head><body>"
        f"{content.replace('__NONCE__', nonce)}"
        "</body></html>"
    )
    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": (
                "default-src 'none'; "
                f"script-src 'nonce-{nonce}'; "
                "style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
            ),
        },
    )


@router.post("/register", response_model=Accepted, status_code=202)
def register(
    *,
    request: Request,
    background_tasks: BackgroundTasks,
    body: Registration,
    database: DatabaseDep,
    auth_settings: AuthSettingsDep,
    app_settings: AppSettingsDep,
) -> Accepted:
    _require_allowed_origin(request, auth_settings, app_settings)
    message, limited = create_account(
        database,
        auth_settings,
        email=str(body.email),
        password=body.password,
        client_ip=_client_ip(request),
    )
    _require_rate_limit_not_exceeded(limited)
    _schedule_email(background_tasks, auth_settings, message)
    return Accepted()


@router.post("/verification-requests", response_model=Accepted, status_code=202)
def send_verification(
    *,
    request: Request,
    background_tasks: BackgroundTasks,
    body: VerificationRequest,
    database: DatabaseDep,
    auth_settings: AuthSettingsDep,
    app_settings: AppSettingsDep,
) -> Accepted:
    _require_allowed_origin(request, auth_settings, app_settings)
    message, limited = request_verification(
        database,
        auth_settings,
        email=str(body.email),
        client_ip=_client_ip(request),
    )
    _require_rate_limit_not_exceeded(limited)
    _schedule_email(background_tasks, auth_settings, message)
    return Accepted()


@router.get("/verify-email", response_class=HTMLResponse, include_in_schema=False)
def verify_email_page() -> HTMLResponse:
    return _auth_page(
        "<main><h1>Verify your email</h1><p id=\"status\">Checking the verification link…</p>"
        "<script nonce=\"__NONCE__\">"
        "const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);"
        "const status=document.getElementById('status');"
        "if(!token){status.textContent='This verification link is missing its token.';}"
        "else{fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({token})}).then(async r=>{const b=await r.json();"
        "status.textContent=r.ok?'Email verified. You can now sign in.':"
        "(b.error?.message||'This link is invalid or expired.');})"
        ".catch(()=>{status.textContent='Verification could not be completed. Try again.';});}"
        "</script></main>"
    )


@router.post("/verify-email", response_model=Verified)
def confirm_email(
    *,
    request: Request,
    body: TokenRequest,
    database: DatabaseDep,
    auth_settings: AuthSettingsDep,
    app_settings: AppSettingsDep,
) -> Verified:
    _require_allowed_origin(request, auth_settings, app_settings)
    if not verify_email(database, body.token):
        raise HTTPException(400, "The verification link is invalid or expired.")
    return Verified()


@router.post("/sessions", response_model=LoginResponse)
def create_session(
    *,
    request: Request,
    body: LoginRequest,
    database: DatabaseDep,
    auth_settings: AuthSettingsDep,
    app_settings: AppSettingsDep,
) -> JSONResponse:
    _require_allowed_origin(request, auth_settings, app_settings)
    result, limited = authenticate(
        database,
        auth_settings,
        email=str(body.email),
        password=body.password,
        client_ip=_client_ip(request),
    )
    _require_rate_limit_not_exceeded(limited)
    if result is None:
        raise HTTPException(401, "Invalid email or password.")

    extension_origin = f"chrome-extension://{app_settings.extension_id}"
    body_values = LoginResponse(
        account_id=result.account_id,
        email=result.email,
        access_token=result.token if request.headers.get("origin") == extension_origin else None,
        token_type="Bearer" if request.headers.get("origin") == extension_origin else None,
        expires_in=result.expires_in,
    )
    response = JSONResponse(
        body_values.model_dump(mode="json", exclude_none=True),
        headers={"Cache-Control": "no-store"},
    )
    if request.headers.get("origin") != extension_origin:
        response.set_cookie(
            COOKIE_NAME,
            result.token,
            max_age=result.expires_in,
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
    return response


@router.post("/password-reset-requests", response_model=Accepted, status_code=202)
def send_password_reset(
    *,
    request: Request,
    background_tasks: BackgroundTasks,
    body: VerificationRequest,
    database: DatabaseDep,
    auth_settings: AuthSettingsDep,
    app_settings: AppSettingsDep,
) -> Accepted:
    _require_allowed_origin(request, auth_settings, app_settings)
    message, limited = request_password_reset(
        database,
        auth_settings,
        email=str(body.email),
        client_ip=_client_ip(request),
    )
    _require_rate_limit_not_exceeded(limited)
    _schedule_email(background_tasks, auth_settings, message)
    return Accepted()


@router.get("/password-reset", response_class=HTMLResponse, include_in_schema=False)
def password_reset_page() -> HTMLResponse:
    return _auth_page(
        "<main><h1>Reset your password</h1>"
        "<form id=\"reset\"><label>New password "
        "<input name=\"password\" type=\"password\" minlength=\"12\" maxlength=\"128\" "
        "autocomplete=\"new-password\" required></label>"
        "<button type=\"submit\">Update password</button></form><p id=\"status\"></p>"
        "<script nonce=\"__NONCE__\">"
        "const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);"
        "const form=document.getElementById('reset');const status=document.getElementById('status');"
        "form.addEventListener('submit',async e=>{e.preventDefault();"
        "const password=new FormData(form).get('password');"
        "try{const r=await fetch(location.pathname.replace(/password-reset$/,'password-resets'),"
        "{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({token,password})});const b=await r.json();"
        "status.textContent=r.ok?'Password updated. You can now sign in.':"
        "(b.error?.message||'This link is invalid or expired.');"
        "if(r.ok)form.remove();}catch{status.textContent='The password could not be updated. Try again.';}});"
        "if(!token){form.remove();status.textContent='This reset link is missing its token.';}"
        "</script></main>"
    )


@router.post("/password-resets", response_model=PasswordUpdated)
def update_password(
    *,
    request: Request,
    body: PasswordReset,
    database: DatabaseDep,
    auth_settings: AuthSettingsDep,
    app_settings: AppSettingsDep,
) -> PasswordUpdated:
    _require_allowed_origin(request, auth_settings, app_settings)
    updated, limited = reset_password(
        database,
        auth_settings,
        token=body.token,
        password=body.password,
        client_ip=_client_ip(request),
    )
    _require_rate_limit_not_exceeded(limited)
    if not updated:
        raise HTTPException(400, "The reset link is invalid or expired.")
    return PasswordUpdated()


@router.get("/me", response_model=AuthenticatedUser)
def current_user(identity: CurrentIdentityDep) -> AuthenticatedUser:
    _, user = identity
    return AuthenticatedUser(
        account_id=user.account_id,
        email=user.email,
        email_verified=user.email_verified_at is not None,
    )


@router.post("/logout", status_code=204)
def logout(
    *,
    request: Request,
    response: Response,
    identity: CurrentIdentityDep,
    database: DatabaseDep,
    auth_settings: AuthSettingsDep,
    app_settings: AppSettingsDep,
) -> Response:
    _require_allowed_origin(request, auth_settings, app_settings)
    auth_session, _ = identity
    revoke_session(database, auth_session.id)
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")
    response.status_code = 204
    return response

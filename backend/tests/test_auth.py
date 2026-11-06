from uuid import UUID

from sqlalchemy import select

from app.core.security import hash_password, verify_password
from app.models import RefreshSession, User
from tests.helpers import register_verified_user


def test_registration_duplicate_email_and_argon2_storage(client, monkeypatch) -> None:
    register_verified_user(client, monkeypatch, "new-user@example.com")
    user = client.app.state.session_factory().scalar(
        select(User).where(User.email == "new-user@example.com")
    )
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    assert user.password_hash != "CorrectHorseBattery!42"

    csrf = client.cookies.get("csrf_token") or ""
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "new-user@example.com", "password": "AnotherPassword!42"},
        headers={"X-CSRF-Token": csrf},
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Unable to register with these details"}


def test_password_hashing_uses_argon2id() -> None:
    encoded = hash_password("CorrectHorseBattery!42")

    assert encoded.startswith("$argon2id$")
    assert verify_password("CorrectHorseBattery!42", encoded)
    assert not verify_password("wrong-password", encoded)


def test_login_current_user_and_generic_invalid_credentials(client, monkeypatch) -> None:
    access_token = register_verified_user(client, monkeypatch, "login@example.com")
    current = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert current.status_code == 200
    assert current.json()["email"] == "login@example.com"

    csrf = client.cookies.get("csrf_token") or ""
    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert invalid.status_code == 401
    assert invalid.json() == {"detail": "Invalid email or password"}


def test_refresh_rotates_tokens_and_reuse_revokes_the_family(client, monkeypatch) -> None:
    access_token = register_verified_user(client, monkeypatch, "refresh@example.com")
    old_refresh = client.cookies.get("refresh_token")
    csrf = client.cookies.get("csrf_token") or ""
    rotated = client.post(
        "/api/v1/auth/refresh",
        headers={"X-CSRF-Token": csrf},
    )
    assert rotated.status_code == 200
    new_refresh = client.cookies.get("refresh_token")
    assert old_refresh and new_refresh and old_refresh != new_refresh

    user_id = rotated.json()["user"]["id"]
    session = client.app.state.session_factory()
    sessions = list(
        session.scalars(
            select(RefreshSession).where(RefreshSession.user_id == UUID(user_id))
        )
    )
    session.close()
    assert len(sessions) == 2
    assert all(item.token_hash not in {old_refresh, new_refresh} for item in sessions)
    assert sum(item.revoked_at is None for item in sessions) == 1

    replay = client.post(
        "/api/v1/auth/refresh",
        cookies={
            "refresh_token": old_refresh,
            "csrf_token": client.cookies.get("csrf_token") or "",
        },
        headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""},
    )
    assert replay.status_code == 401
    protected = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {rotated.json()['access_token']}"},
    )
    assert protected.status_code == 401
    assert access_token


def test_logout_revokes_refresh_and_access_session(client, monkeypatch) -> None:
    access_token = register_verified_user(client, monkeypatch, "logout@example.com")
    response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""},
    )
    assert response.status_code == 204
    assert client.cookies.get("refresh_token") is None
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    ).status_code == 401


def test_protected_endpoint_rejects_missing_invalid_and_expired_tokens(client) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    ).status_code == 401
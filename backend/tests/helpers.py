from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def register_verified_user(
    client: TestClient,
    monkeypatch: MonkeyPatch,
    email: str,
) -> str:
    sent_messages: list[tuple] = []
    monkeypatch.setattr(
        "app.api.v1.auth.send_email",
        lambda *args: sent_messages.append(args),
    )
    client.get("/api/v1/auth/csrf")
    csrf_token = client.cookies.get("csrf_token")
    csrf_headers = {"X-CSRF-Token": csrf_token or ""}
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "CorrectHorseBattery!42"},
        headers=csrf_headers,
    )
    assert registration.status_code == 201
    assert sent_messages

    verification_link = sent_messages[-1][-1].splitlines()[0].split(" ", 1)[-1]
    verification_token = parse_qs(urlparse(verification_link).query)["token"][0]
    verified = client.post(
        "/api/v1/auth/verify-email",
        json={"token": verification_token},
        headers=csrf_headers,
    )
    assert verified.status_code == 200

    csrf_headers["X-CSRF-Token"] = client.cookies.get("csrf_token") or ""
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "CorrectHorseBattery!42"},
        headers=csrf_headers,
    )
    assert login.status_code == 200
    return login.json()["access_token"]
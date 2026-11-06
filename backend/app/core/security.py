import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings

_password_hasher = PasswordHasher(
	time_cost=3,
	memory_cost=65_536,
	parallelism=2,
	hash_len=32,
	salt_len=16,
	type=Type.ID,
)
_dummy_password_hash = _password_hasher.hash("not-a-valid-user-password")


def hash_password(password: str) -> str:
	return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
	encoded = password_hash or _dummy_password_hash
	try:
		return _password_hasher.verify(encoded, password) and password_hash is not None
	except (InvalidHashError, VerificationError, VerifyMismatchError):
		return False


def needs_password_rehash(password_hash: str) -> bool:
	return _password_hasher.check_needs_rehash(password_hash)


def create_access_token(
	user_id: str,
	session_id: str,
	settings: Settings,
) -> tuple[str, int]:
	expires_in = settings.auth_access_token_minutes * 60
	now = datetime.now(UTC)
	token = jwt.encode(
		{
			"sub": user_id,
			"sid": session_id,
			"type": "access",
			"iat": now,
			"exp": now + timedelta(seconds=expires_in),
			"iss": "sirapilot-ai",
		},
		settings.secret_key.get_secret_value(),
		algorithm="HS256",
	)
	return token, expires_in


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
	return jwt.decode(
		token,
		settings.secret_key.get_secret_value(),
		algorithms=["HS256"],
		issuer="sirapilot-ai",
		options={"require": ["sub", "sid", "exp", "iat", "type"]},
	)


def create_opaque_token() -> str:
	return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_csrf_token(settings: Settings) -> str:
	value = secrets.token_urlsafe(32)
	signature = hmac.new(
		settings.secret_key.get_secret_value().encode("utf-8"),
		value.encode("utf-8"),
		hashlib.sha256,
	).hexdigest()
	return f"{value}.{signature}"


def is_valid_csrf_token(cookie_value: str | None, header_value: str | None, settings: Settings) -> bool:
	if not cookie_value or not header_value or not hmac.compare_digest(cookie_value, header_value):
		return False
	try:
		value, signature = cookie_value.rsplit(".", 1)
	except ValueError:
		return False
	expected = hmac.new(
		settings.secret_key.get_secret_value().encode("utf-8"),
		value.encode("utf-8"),
		hashlib.sha256,
	).hexdigest()
	return hmac.compare_digest(signature, expected)

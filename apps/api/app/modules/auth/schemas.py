"""Public request and response contracts for account authentication."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator

Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
OpaqueToken = Annotated[str, StringConstraints(min_length=32, max_length=256)]


class AuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(AuthRequest):
    email: EmailStr
    password: Password

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()


class Registration(Credentials):
    """New account credentials."""


class VerificationRequest(AuthRequest):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()


class LoginRequest(Credentials):
    """Credentials for an existing account."""


class TokenRequest(AuthRequest):
    token: OpaqueToken


class PasswordReset(AuthRequest):
    token: OpaqueToken
    password: Password


class LoginResponse(BaseModel):
    account_id: UUID
    email: EmailStr
    access_token: str | None = None
    token_type: str | None = None
    expires_in: int


class AuthenticatedUser(BaseModel):
    account_id: UUID
    email: EmailStr
    email_verified: bool


class Accepted(BaseModel):
    status: str = "accepted"


class Verified(BaseModel):
    status: str = "verified"


class PasswordUpdated(BaseModel):
    status: str = "password_updated"

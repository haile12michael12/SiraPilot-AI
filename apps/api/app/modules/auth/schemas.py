"""Public request and response contracts for account authentication."""

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
OpaqueToken = Annotated[str, StringConstraints(min_length=32, max_length=256)]


class AuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Registration(AuthRequest):
    email: EmailStr
    password: Password

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()


class VerificationRequest(AuthRequest):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()


class LoginRequest(Registration):
    pass


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


def reject_email_whitespace(value: str) -> str:
    if value != value.strip():
        raise ValueError("email cannot contain surrounding whitespace")
    return value

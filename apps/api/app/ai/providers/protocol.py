"""Provider adapter protocol and normalized result types."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.contracts import AIMessage
from app.ai.usage import TokenUsage


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1, max_length=128)
    messages: list[AIMessage] = Field(min_length=1, max_length=100)
    response_schema: dict[str, Any]
    max_output_tokens: int = Field(ge=1, le=32768)
    temperature: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _requires_user_message(self) -> ProviderRequest:
        if not any(message.role == "user" for message in self.messages):
            raise ValueError("At least one user message is required")
        return self


class ProviderResponse(BaseModel):
    content: str
    finish_reason: str | None = None
    usage: TokenUsage


class AIProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    async def generate(self, request: ProviderRequest) -> ProviderResponse: ...

"""Typed provider-independent AI inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.usage import UsageRecord


class AIMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=100_000)


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_alias: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    feature: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    prompt_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.-]+$")
    prompt_version: str = Field(min_length=1, max_length=64)
    messages: list[AIMessage] = Field(min_length=1, max_length=100)
    max_output_tokens: int | None = Field(default=None, ge=1, le=32768)
    temperature: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _validate_messages(self) -> GenerationRequest:
        if not any(message.role == "user" for message in self.messages):
            raise ValueError("At least one user message is required")
        if sum(len(message.content) for message in self.messages) > 1_000_000:
            raise ValueError("Combined message content exceeds the maximum input size")
        return self


@dataclass(frozen=True)
class GeneratedResponse[T: BaseModel]:
    value: T
    usage: UsageRecord


@dataclass(frozen=True)
class StructuredPayload:
    """Normalized JSON-object content returned by a provider adapter."""

    value: dict[str, Any]

"""Anthropic Messages API adapter using a forced structured-output tool."""

from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, SecretStr, ValidationError

from app.ai.errors import AIProviderError
from app.ai.providers.protocol import ProviderRequest, ProviderResponse
from app.ai.usage import TokenUsage

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
_STRUCTURED_TOOL = "structured_response"


class _AnthropicBlock(BaseModel):
    type: str
    name: str | None = None
    input: dict[str, Any] | None = None


class _AnthropicUsage(BaseModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class _AnthropicResponse(BaseModel):
    content: list[_AnthropicBlock] = Field(min_length=1)
    stop_reason: str | None = None
    usage: _AnthropicUsage | None = None


class AnthropicAdapter:
    provider_name = "anthropic"

    def __init__(self, *, api_key: SecretStr, client: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._client = client

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        system = "\n\n".join(
            message.content for message in request.messages if message.role == "system"
        )
        messages = [
            message.model_dump(mode="json")
            for message in request.messages
            if message.role != "system"
        ]
        if not messages:
            raise AIProviderError(self.provider_name, "user_message_required")

        payload: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "messages": messages,
            "tools": [
                {
                    "name": _STRUCTURED_TOOL,
                    "description": "Return the requested structured response.",
                    "input_schema": request.response_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": _STRUCTURED_TOOL},
        }
        if system:
            payload["system"] = system
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        try:
            response = await self._client.post(
                ANTHROPIC_MESSAGES_URL,
                headers={
                    "x-api-key": self._api_key.get_secret_value(),
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json=payload,
            )
        except httpx.RequestError:
            raise AIProviderError(self.provider_name, "transport_error", retryable=True) from None

        if response.is_error:
            raise AIProviderError(
                self.provider_name,
                "http_error",
                retryable=response.status_code == 429 or response.status_code >= 500,
                status_code=response.status_code,
            )

        try:
            body = _AnthropicResponse.model_validate(response.json())
        except ValueError, ValidationError:
            raise AIProviderError(self.provider_name, "invalid_response") from None

        structured_block = next(
            (
                block
                for block in body.content
                if block.type == "tool_use"
                and block.name == _STRUCTURED_TOOL
                and block.input is not None
            ),
            None,
        )
        if structured_block is None or structured_block.input is None:
            return ProviderResponse(
                content="",
                finish_reason=body.stop_reason,
                usage=TokenUsage(
                    input_tokens=body.usage.input_tokens if body.usage else None,
                    output_tokens=body.usage.output_tokens if body.usage else None,
                ),
            )

        return ProviderResponse(
            content=json.dumps(structured_block.input, separators=(",", ":"), ensure_ascii=False),
            finish_reason=body.stop_reason,
            usage=TokenUsage(
                input_tokens=body.usage.input_tokens if body.usage else None,
                output_tokens=body.usage.output_tokens if body.usage else None,
            ),
        )

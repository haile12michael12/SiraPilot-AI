"""OpenAI Chat Completions adapter and shared OpenAI-compatible transport."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field, SecretStr, ValidationError

from app.ai.errors import AIProviderError
from app.ai.providers.protocol import ProviderRequest, ProviderResponse
from app.ai.usage import TokenUsage

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


class _OpenAIMessage(BaseModel):
    content: str | None = None
    refusal: str | None = None


class _OpenAIChoice(BaseModel):
    message: _OpenAIMessage
    finish_reason: str | None = None


class _OpenAIUsage(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)


class _OpenAIResponse(BaseModel):
    choices: list[_OpenAIChoice] = Field(min_length=1)
    usage: _OpenAIUsage | None = None


class OpenAICompatibleAdapter:
    def __init__(
        self,
        *,
        provider_name: str,
        base_url: str,
        api_key: SecretStr | None,
        client: httpx.AsyncClient,
        strict_json_schema: bool,
    ) -> None:
        self._provider_name = provider_name
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._client = client
        self._strict_json_schema = strict_json_schema

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        headers = {"Content-Type": "application/json"}
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key.get_secret_value()}"

        response_format: dict[str, Any]
        if self._strict_json_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": _strict_schema(request.response_schema),
                },
            }
        else:
            response_format = {"type": "json_object"}

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [message.model_dump(mode="json") for message in request.messages],
            "max_completion_tokens": request.max_output_tokens,
            "response_format": response_format,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        try:
            response = await self._client.post(self._url, headers=headers, json=payload)
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
            body = _OpenAIResponse.model_validate(response.json())
        except ValueError, ValidationError:
            raise AIProviderError(self.provider_name, "invalid_response") from None

        choice = body.choices[0]
        usage = body.usage
        is_refusal = choice.message.refusal is not None
        return ProviderResponse(
            content="{}" if is_refusal else choice.message.content or "",
            finish_reason="refusal" if is_refusal else choice.finish_reason,
            usage=TokenUsage(
                input_tokens=usage.prompt_tokens if usage else None,
                output_tokens=usage.completion_tokens if usage else None,
            ),
        )


class OpenAIAdapter(OpenAICompatibleAdapter):
    def __init__(self, *, api_key: SecretStr, client: httpx.AsyncClient) -> None:
        super().__init__(
            provider_name="openai",
            base_url="https://api.openai.com/v1",
            api_key=api_key,
            client=client,
            strict_json_schema=True,
        )


def _strict_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [_strict_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    schema = {key: _strict_schema(item) for key, item in value.items() if key != "default"}
    if schema.get("type") == "object":
        properties = schema.get("properties", {})
        schema["required"] = list(properties)
        schema["additionalProperties"] = False
    return schema

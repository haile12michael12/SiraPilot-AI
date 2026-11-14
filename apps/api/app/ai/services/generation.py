"""Provider-independent structured generation service."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.contracts import AIMessage, GeneratedResponse, GenerationRequest
from app.ai.errors import AIInputValidationError, AIOutputValidationError
from app.ai.providers.protocol import ProviderRequest
from app.ai.providers.registry import ProviderRegistry
from app.ai.usage import UsageRecorder, build_usage_record

T = TypeVar("T", bound=BaseModel)


class StructuredGenerator(Protocol):
    async def generate(
        self, request: GenerationRequest, response_model: type[T]
    ) -> GeneratedResponse[T]: ...


class AIService:
    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        usage_recorder: UsageRecorder,
        max_output_tokens: int,
        max_input_characters: int,
        close: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._registry = registry
        self._usage_recorder = usage_recorder
        self._max_output_tokens = max_output_tokens
        self._max_input_characters = max_input_characters
        self._close = close

    async def __aenter__(self) -> AIService:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._close is not None:
            await self._close()

    async def generate(
        self, request: GenerationRequest, response_model: type[T]
    ) -> GeneratedResponse[T]:
        resolved = self._registry.resolve(request.model_alias)
        output_schema = response_model.model_json_schema()
        schema_instruction = "Return only a JSON object matching this JSON Schema:\n" + json.dumps(
            output_schema, separators=(",", ":"), ensure_ascii=False
        )
        messages = [AIMessage(role="system", content=schema_instruction), *request.messages]
        input_characters = sum(len(message.content) for message in messages)
        if input_characters > self._max_input_characters:
            raise AIInputValidationError("AI request exceeds the configured input limit")

        max_output_tokens = min(
            request.max_output_tokens or self._max_output_tokens, self._max_output_tokens
        )
        provider_request = ProviderRequest(
            model=resolved.route.model,
            messages=messages,
            response_schema=output_schema,
            max_output_tokens=max_output_tokens,
            temperature=request.temperature,
        )

        started = perf_counter()
        provider_response = await resolved.provider.generate(provider_request)
        duration_ms = max(0, round((perf_counter() - started) * 1000))
        usage = build_usage_record(
            feature=request.feature,
            prompt_id=request.prompt_id,
            prompt_version=request.prompt_version,
            model_alias=request.model_alias,
            provider=resolved.provider.provider_name,
            model=resolved.route.model,
            token_usage=provider_response.usage,
            duration_ms=duration_ms,
            route=resolved.route,
        )
        await self._usage_recorder.record(usage)

        if provider_response.finish_reason in {"length", "max_tokens", "content_filter", "refusal"}:
            raise AIOutputValidationError("AI response was incomplete or blocked")

        try:
            payload = json.loads(provider_response.content)
        except json.JSONDecodeError:
            raise AIOutputValidationError("AI response was not valid JSON") from None
        try:
            value = response_model.model_validate(payload, strict=True, extra="forbid")
        except ValidationError:
            raise AIOutputValidationError(
                "AI response did not match the requested output schema"
            ) from None
        return GeneratedResponse(value=value, usage=usage)

"""Construct an AI service from explicit application settings."""

from __future__ import annotations

import httpx
from pydantic import AnyHttpUrl, SecretStr

from app.ai.errors import AIConfigurationError
from app.ai.providers.protocol import AIProvider
from app.ai.providers.registry import ProviderRegistry
from app.ai.services.generation import AIService
from app.ai.usage import UsageRecorder
from app.config import Settings
from app.integrations.ai.anthropic import AnthropicAdapter
from app.integrations.ai.local import LocalModelAdapter
from app.integrations.ai.openai import OpenAIAdapter


def build_ai_service(
    settings: Settings, *, usage_recorder: UsageRecorder, client: httpx.AsyncClient | None = None
) -> AIService:
    routes = settings.ai_model_routes
    if not routes:
        raise AIConfigurationError("No AI model routes are configured")

    required_providers = {route.provider for route in routes.values()}
    api_keys: dict[str, SecretStr] = {}
    if "openai" in required_providers:
        if settings.ai_openai_api_key is None:
            raise AIConfigurationError("AI_OPENAI_API_KEY is required by a configured route")
        api_keys["openai"] = settings.ai_openai_api_key
    if "anthropic" in required_providers:
        if settings.ai_anthropic_api_key is None:
            raise AIConfigurationError("AI_ANTHROPIC_API_KEY is required by a configured route")
        api_keys["anthropic"] = settings.ai_anthropic_api_key

    local_urls: dict[str, AnyHttpUrl] = {}
    if "local" in required_providers:
        if settings.ai_local_base_url is None:
            raise AIConfigurationError("AI_LOCAL_BASE_URL is required by a configured route")
        local_urls["local"] = settings.ai_local_base_url

    owns_client = client is None
    http_client = client if client is not None else _client(settings)
    providers: dict[str, AIProvider] = {}
    if "openai" in required_providers:
        providers["openai"] = OpenAIAdapter(api_key=api_keys["openai"], client=http_client)
    if "anthropic" in required_providers:
        providers["anthropic"] = AnthropicAdapter(api_key=api_keys["anthropic"], client=http_client)
    if "local" in required_providers:
        providers["local"] = LocalModelAdapter(
            base_url=local_urls["local"], api_key=settings.ai_local_api_key, client=http_client
        )

    return AIService(
        registry=ProviderRegistry(providers, routes),
        usage_recorder=usage_recorder,
        max_output_tokens=settings.ai_max_output_tokens,
        max_input_characters=settings.ai_max_input_characters,
        close=http_client.aclose if owns_client else None,
    )


def _client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds)

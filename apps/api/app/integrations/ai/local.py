"""Optional adapter for a configured OpenAI-compatible local model endpoint."""

from __future__ import annotations

import httpx
from pydantic import AnyHttpUrl, SecretStr

from app.integrations.ai.openai import OpenAICompatibleAdapter


class LocalModelAdapter(OpenAICompatibleAdapter):
    def __init__(
        self, *, base_url: AnyHttpUrl, client: httpx.AsyncClient, api_key: SecretStr | None = None
    ) -> None:
        super().__init__(
            provider_name="local",
            base_url=str(base_url),
            api_key=api_key,
            client=client,
            strict_json_schema=False,
        )

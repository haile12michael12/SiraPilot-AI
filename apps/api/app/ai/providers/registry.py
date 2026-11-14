"""Explicit logical-model routing without provider references in features."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.ai.errors import AIConfigurationError
from app.ai.providers.protocol import AIProvider
from app.config import AIModelRoute


@dataclass(frozen=True)
class ResolvedProvider:
    provider: AIProvider
    route: AIModelRoute


class ProviderRegistry:
    def __init__(
        self, providers: Mapping[str, AIProvider], routes: Mapping[str, AIModelRoute]
    ) -> None:
        if not routes:
            raise AIConfigurationError("No AI model routes are configured")
        self._providers = dict(providers)
        self._routes = dict(routes)
        missing = {route.provider for route in routes.values()} - self._providers.keys()
        if missing:
            names = ", ".join(sorted(missing))
            raise AIConfigurationError(f"AI providers are not configured: {names}")

    def resolve(self, model_alias: str) -> ResolvedProvider:
        route = self._routes.get(model_alias)
        if route is None:
            raise AIConfigurationError(f"AI model alias is not configured: {model_alias}")
        return ResolvedProvider(self._providers[route.provider], route)

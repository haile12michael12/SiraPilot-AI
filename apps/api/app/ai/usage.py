"""Privacy-minimal token and estimated-cost usage records."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.config import AIModelRoute

_MILLION = Decimal(1_000_000)
_COST_QUANTUM = Decimal("0.00000001")


class TokenUsage(BaseModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class UsageRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    feature: str
    prompt_id: str
    prompt_version: str
    model_alias: str
    provider: str
    model: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    duration_ms: int = Field(ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    pricing_version: str | None = None


class UsageRecorder(Protocol):
    async def record(self, usage: UsageRecord) -> None: ...


def build_usage_record(
    *,
    feature: str,
    prompt_id: str,
    prompt_version: str,
    model_alias: str,
    provider: str,
    model: str,
    token_usage: TokenUsage,
    duration_ms: int,
    route: AIModelRoute,
) -> UsageRecord:
    estimated_cost: Decimal | None = None
    currency: str | None = None
    pricing_version: str | None = None
    if (
        token_usage.input_tokens is not None
        and token_usage.output_tokens is not None
        and route.input_cost_per_million is not None
        and route.output_cost_per_million is not None
    ):
        estimated_cost = (
            Decimal(token_usage.input_tokens) * route.input_cost_per_million
            + Decimal(token_usage.output_tokens) * route.output_cost_per_million
        ) / _MILLION
        estimated_cost = estimated_cost.quantize(_COST_QUANTUM, rounding=ROUND_HALF_UP)
        currency = route.currency
        pricing_version = route.pricing_version

    return UsageRecord(
        feature=feature,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        model_alias=model_alias,
        provider=provider,
        model=model,
        input_tokens=token_usage.input_tokens,
        output_tokens=token_usage.output_tokens,
        duration_ms=duration_ms,
        estimated_cost=estimated_cost,
        currency=currency,
        pricing_version=pricing_version,
    )

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Any, TypeVar

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, SecretStr

from app.ai.contracts import AIMessage, GeneratedResponse, GenerationRequest
from app.ai.errors import AIConfigurationError, AIOutputValidationError, PromptInputError
from app.ai.evaluation.runner import EvaluationCase, evaluate_cases
from app.ai.orchestration.agents import AgentOrchestrator, AgentTool
from app.ai.prompts.registry import PromptDefinition, PromptRegistry
from app.ai.providers.protocol import ProviderRequest
from app.ai.usage import UsageRecord
from app.config import AIModelRoute, Settings
from app.integrations.ai.anthropic import AnthropicAdapter
from app.integrations.ai.factory import build_ai_service

T = TypeVar("T", bound=BaseModel)


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    rank: int = 7


class MemoryUsageRecorder:
    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    async def record(self, usage: UsageRecord) -> None:
        self.records.append(usage)


def _request() -> GenerationRequest:
    return GenerationRequest(
        model_alias="drafting",
        feature="test",
        prompt_id="answer",
        prompt_version="1",
        messages=[
            AIMessage(role="system", content="Follow the schema."),
            AIMessage(role="user", content="Give an answer."),
        ],
    )


def _usage() -> UsageRecord:
    return UsageRecord(
        feature="test",
        prompt_id="answer",
        prompt_version="1",
        model_alias="drafting",
        provider="test",
        model="test-model",
        duration_ms=0,
    )


class ScriptedGenerator:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = iter(responses)

    async def generate(
        self, request: GenerationRequest, response_model: type[T]
    ) -> GeneratedResponse[T]:
        del request
        value = response_model.model_validate(next(self._responses), extra="forbid")
        return GeneratedResponse(value=value, usage=_usage())


def test_openai_route_validates_and_records_usage_offline() -> None:
    async def exercise() -> None:
        captured: dict[str, Any] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            captured["payload"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {"content": '{"answer":"ready","rank":3}'},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )

        recorder = MemoryUsageRecorder()
        settings = Settings(
            ai_model_routes={
                "drafting": AIModelRoute(
                    provider="openai",
                    model="configured-model",
                    input_cost_per_million=Decimal("2"),
                    output_cost_per_million=Decimal("4"),
                    pricing_version="test-rates",
                )
            },
            ai_openai_api_key=SecretStr("test-secret"),
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = build_ai_service(settings, usage_recorder=recorder, client=client)
            async with service:
                result = await service.generate(_request(), Answer)

        assert result.value == Answer(answer="ready", rank=3)
        assert len(recorder.records) == 1
        assert recorder.records[0].estimated_cost == Decimal("0.00004000")
        assert recorder.records[0].pricing_version == "test-rates"
        assert captured["headers"]["authorization"] == "Bearer test-secret"
        schema = captured["payload"]["response_format"]["json_schema"]["schema"]
        assert schema["required"] == ["answer", "rank"]
        assert schema["additionalProperties"] is False
        assert "default" not in schema["properties"]["rank"]
        assert captured["payload"]["model"] == "configured-model"

    asyncio.run(exercise())


def test_invalid_structured_output_is_recorded_before_error() -> None:
    async def exercise() -> None:
        async def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 1},
                },
            )

        recorder = MemoryUsageRecorder()
        settings = Settings(
            ai_model_routes={"drafting": AIModelRoute(provider="openai", model="configured-model")},
            ai_openai_api_key=SecretStr("test-secret"),
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = build_ai_service(settings, usage_recorder=recorder, client=client)
            with pytest.raises(AIOutputValidationError):
                await service.generate(_request(), Answer)
        assert len(recorder.records) == 1

    asyncio.run(exercise())


def test_anthropic_adapter_uses_structured_tool_and_normalizes_usage() -> None:
    async def exercise() -> None:
        captured: dict[str, Any] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = request.headers
            captured["payload"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "structured_response",
                            "input": {"answer": "ready", "rank": 3},
                        }
                    ],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 9, "output_tokens": 4},
                },
            )

        request = _request()
        provider_request = ProviderRequest(
            model="configured-model",
            messages=request.messages,
            response_schema=Answer.model_json_schema(),
            max_output_tokens=128,
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = AnthropicAdapter(api_key=SecretStr("test-secret"), client=client)
            result = await adapter.generate(provider_request)

        assert json.loads(result.content) == {"answer": "ready", "rank": 3}
        assert result.usage.input_tokens == 9
        assert captured["headers"]["x-api-key"] == "test-secret"
        assert captured["payload"]["tool_choice"] == {"type": "tool", "name": "structured_response"}

    asyncio.run(exercise())


def test_local_route_uses_configured_endpoint_without_cloud_credentials() -> None:
    async def exercise() -> None:
        captured: dict[str, Any] = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = request.headers
            return httpx.Response(
                200, json={"choices": [{"message": {"content": '{"answer":"local","rank":1}'}}]}
            )

        settings = Settings(
            ai_model_routes={"drafting": AIModelRoute(provider="local", model="local-model")},
            ai_local_base_url="http://127.0.0.1:1234/v1",
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = build_ai_service(
                settings, usage_recorder=MemoryUsageRecorder(), client=client
            )
            result = await service.generate(_request(), Answer)

        assert result.value.answer == "local"
        assert captured["url"] == "http://127.0.0.1:1234/v1/chat/completions"
        assert "authorization" not in captured["headers"]

    asyncio.run(exercise())


def test_prompt_registry_versions_and_rejects_unknown_input() -> None:
    class PromptInput(BaseModel):
        question: str

    prompt = PromptDefinition(
        prompt_id="answer",
        version="2",
        system_prompt="Be concise.",
        user_template="Question: $question",
        input_model=PromptInput,
        output_model=Answer,
    )
    registry = PromptRegistry()
    registry.register(prompt)

    request = registry.resolve("answer", "2").render(
        model_alias="drafting", feature="test", values={"question": "Why?"}
    )
    assert request.prompt_version == "2"
    assert request.messages[-1].content == "Question: Why?"
    with pytest.raises(PromptInputError):
        prompt.render(
            model_alias="drafting",
            feature="test",
            values={"question": "Why?", "untrusted": "ignored otherwise"},
        )


def test_agent_returns_consequential_action_for_approval() -> None:
    class ActionInput(BaseModel):
        name: str

    class ActionOutput(BaseModel):
        done: bool

    async def execute(_: ActionInput) -> ActionOutput:
        raise AssertionError("approval-required tools must not execute")

    orchestrator = AgentOrchestrator(
        ScriptedGenerator(
            [
                {
                    "kind": "tool_call",
                    "tool_name": "create_profile",
                    "arguments": {"name": "candidate"},
                    "summary": "Create a profile.",
                }
            ]
        ),
        [
            AgentTool(
                name="create_profile",
                description="Create a profile.",
                input_model=ActionInput,
                output_model=ActionOutput,
                execute=execute,
            )
        ],
        max_steps=2,
        max_tool_calls=2,
    )

    result = asyncio.run(orchestrator.run(_request()))
    assert result.status == "approval_required"
    assert result.pending_action is not None
    assert result.pending_action.arguments == {"name": "candidate"}


def test_evaluation_runner_reports_criteria_failures() -> None:
    case = EvaluationCase(
        name="answer",
        request=_request(),
        output_model=Answer,
        accepts=lambda value: value.answer == "expected",
    )
    report = asyncio.run(
        evaluate_cases(ScriptedGenerator([{"answer": "different", "rank": 1}]), (case,))
    )
    assert report.case_count == 1
    assert report.pass_rate == 0
    assert report.failed_cases == ("answer",)


def test_provider_route_without_secret_fails_explicitly() -> None:
    settings = Settings(
        ai_model_routes={"drafting": AIModelRoute(provider="openai", model="configured-model")}
    )
    with pytest.raises(AIConfigurationError, match="AI_OPENAI_API_KEY"):
        build_ai_service(settings, usage_recorder=MemoryUsageRecorder())

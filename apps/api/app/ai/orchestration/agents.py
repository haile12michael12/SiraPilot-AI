"""Bounded tool orchestration; consequential actions are returned for approval."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.ai.contracts import AIMessage, GenerationRequest
from app.ai.errors import AgentError, AgentLimitExceeded
from app.ai.services.generation import StructuredGenerator

_TOOL_NAME = re.compile(r"^[a-zA-Z0-9_.-]+$")
ToolHandler = Callable[[BaseModel], Awaitable[BaseModel]]


class AgentDecision(BaseModel):
    kind: Literal["final", "tool_call"]
    response: str | None = Field(default=None, max_length=20_000)
    tool_name: str | None = Field(default=None, max_length=64)
    arguments: dict[str, Any] | None = None
    summary: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_shape(self) -> AgentDecision:
        if self.kind == "final":
            if not self.response or not self.response.strip():
                raise ValueError("Final agent responses must contain text")
            if self.tool_name is not None or self.arguments is not None or self.summary is not None:
                raise ValueError("Final agent responses cannot include tool-call fields")
        elif (
            self.response is not None
            or self.tool_name is None
            or self.arguments is None
            or self.summary is None
            or not self.summary.strip()
        ):
            raise ValueError("Agent tool calls require a name, arguments, and summary")
        return self


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    execute: ToolHandler
    requires_approval: bool = True

    def __post_init__(self) -> None:
        if not _TOOL_NAME.fullmatch(self.name):
            raise ValueError(
                "Agent tool names may contain only letters, digits, dot, dash, and underscore"
            )
        if not self.description.strip():
            raise ValueError("Agent tools require a description")


@dataclass(frozen=True)
class PendingAction:
    tool_name: str
    summary: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AgentRunResult:
    status: Literal["completed", "approval_required"]
    response: str | None
    pending_action: PendingAction | None
    steps: int
    tool_calls: int


class _ToolRegistry:
    def __init__(self, tools: list[AgentTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("Agent tool names must be unique")

    def resolve(self, name: str) -> AgentTool:
        tool = self._tools.get(name)
        if tool is None:
            raise AgentError("Agent selected an unknown tool")
        return tool

    def descriptions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_model.model_json_schema(),
                "requires_approval": tool.requires_approval,
            }
            for tool in self._tools.values()
        ]


class AgentOrchestrator:
    def __init__(
        self,
        ai_service: StructuredGenerator,
        tools: list[AgentTool],
        *,
        max_steps: int,
        max_tool_calls: int,
    ) -> None:
        if max_steps < 1 or max_steps > 32 or max_tool_calls < 0 or max_tool_calls > 32:
            raise ValueError("Agent limits must be within 1-32 steps and 0-32 tool calls")
        self._ai_service = ai_service
        self._tools = _ToolRegistry(tools)
        self._max_steps = max_steps
        self._max_tool_calls = max_tool_calls

    async def run(self, request: GenerationRequest) -> AgentRunResult:
        catalog = json.dumps(self._tools.descriptions(), separators=(",", ":"), ensure_ascii=False)
        messages = [
            AIMessage(
                role="system",
                content=(
                    "Choose a final response or one tool call. Use only a listed tool and its "
                    "declared arguments. A consequential tool requires user approval; never "
                    "claim that a proposed action has been executed.\nAvailable tools:\n" + catalog
                ),
            ),
            *request.messages,
        ]
        for step in range(1, self._max_steps + 1):
            tool_calls = step - 1
            current_request = GenerationRequest.model_validate(
                request.model_dump(mode="python") | {"messages": messages}
            )
            generated = await self._ai_service.generate(current_request, AgentDecision)
            decision = generated.value
            if decision.kind == "final":
                return AgentRunResult(
                    status="completed",
                    response=decision.response,
                    pending_action=None,
                    steps=step,
                    tool_calls=tool_calls,
                )

            if tool_calls >= self._max_tool_calls:
                raise AgentLimitExceeded("Agent exceeded its configured tool-call limit")
            if step == self._max_steps:
                raise AgentLimitExceeded("Agent exceeded its configured step limit")

            tool = self._tools.resolve(decision.tool_name or "")
            try:
                arguments = tool.input_model.model_validate(
                    decision.arguments, strict=True, extra="forbid"
                )
            except ValidationError:
                raise AgentError(
                    "Agent tool arguments did not match the declared input schema"
                ) from None

            if tool.requires_approval:
                return AgentRunResult(
                    status="approval_required",
                    response=None,
                    pending_action=PendingAction(
                        tool_name=tool.name,
                        summary=decision.summary or "",
                        arguments=arguments.model_dump(mode="json"),
                    ),
                    steps=step,
                    tool_calls=step,
                )

            output = await tool.execute(arguments)
            try:
                validated_output = tool.output_model.model_validate(
                    output, strict=True, extra="forbid"
                )
            except ValidationError:
                raise AgentError(
                    "Agent tool result did not match the declared output schema"
                ) from None

            messages.extend(
                [
                    AIMessage(role="assistant", content=decision.model_dump_json()),
                    AIMessage(
                        role="user",
                        content=json.dumps(
                            {
                                "tool_name": tool.name,
                                "result": validated_output.model_dump(mode="json"),
                            },
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ),
                    ),
                ]
            )

        raise AgentLimitExceeded("Agent exceeded its configured step limit")

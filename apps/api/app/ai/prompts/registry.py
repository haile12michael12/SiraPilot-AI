"""Source-controlled prompt versions with validated, named inputs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from string import Template
from typing import Any

from pydantic import BaseModel, ValidationError

from app.ai.contracts import AIMessage, GenerationRequest
from app.ai.errors import PromptInputError, PromptNotFound

_PROMPT_ID = re.compile(r"^[a-zA-Z0-9_.-]+$")


@dataclass(frozen=True)
class PromptDefinition:
    prompt_id: str
    version: str
    system_prompt: str
    user_template: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]

    def __post_init__(self) -> None:
        if not _PROMPT_ID.fullmatch(self.prompt_id):
            raise ValueError(
                "Prompt identifiers may contain only letters, digits, dot, dash, and underscore"
            )
        if not self.version or len(self.version) > 64:
            raise ValueError("Prompt versions must contain 1 to 64 characters")
        if not self.system_prompt.strip() or not self.user_template.strip():
            raise ValueError("Prompt system text and user template must be non-empty")
        unknown = self._template_fields() - self.input_model.model_fields.keys()
        if unknown:
            raise ValueError("Prompt template references undeclared input fields")

    def _template_fields(self) -> set[str]:
        fields: set[str] = set()
        for match in Template.pattern.finditer(self.user_template):
            if match.group("invalid") is not None:
                raise ValueError("Prompt template contains invalid placeholder syntax")
            name = match.group("named") or match.group("braced")
            if name:
                fields.add(name.split(".", 1)[0].split("[", 1)[0])
        return fields

    def render(
        self,
        *,
        model_alias: str,
        feature: str,
        values: BaseModel | dict[str, Any],
        max_output_tokens: int | None = None,
    ) -> GenerationRequest:
        raw_values = values.model_dump(mode="python") if isinstance(values, BaseModel) else values
        try:
            validated = self.input_model.model_validate(raw_values, strict=True, extra="forbid")
        except ValidationError:
            raise PromptInputError(
                "Prompt inputs did not match the declared input schema"
            ) from None

        context = validated.model_dump(mode="json")
        replacements = {
            key: value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            for key, value in context.items()
        }
        try:
            user_content = Template(self.user_template).substitute(replacements)
        except KeyError, ValueError:
            raise PromptInputError("Prompt inputs could not be rendered") from None

        return GenerationRequest(
            model_alias=model_alias,
            feature=feature,
            prompt_id=self.prompt_id,
            prompt_version=self.version,
            messages=[
                AIMessage(role="system", content=self.system_prompt),
                AIMessage(role="user", content=user_content),
            ],
            max_output_tokens=max_output_tokens,
        )


class PromptRegistry:
    def __init__(self) -> None:
        self._prompts: dict[tuple[str, str], PromptDefinition] = {}

    def register(self, prompt: PromptDefinition) -> None:
        key = (prompt.prompt_id, prompt.version)
        if key in self._prompts:
            raise ValueError("Prompt identifier and version are already registered")
        self._prompts[key] = prompt

    def resolve(self, prompt_id: str, version: str) -> PromptDefinition:
        prompt = self._prompts.get((prompt_id, version))
        if prompt is None:
            raise PromptNotFound(f"Prompt version is not registered: {prompt_id}@{version}")
        return prompt

"""Provider-independent runner for explicit, versioned prompt evaluations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from app.ai.contracts import GenerationRequest
from app.ai.services.generation import StructuredGenerator


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    request: GenerationRequest
    output_model: type[BaseModel]
    accepts: Callable[[BaseModel], bool]


@dataclass(frozen=True)
class EvaluationReport:
    case_count: int
    passed_count: int
    failed_cases: tuple[str, ...]

    @property
    def pass_rate(self) -> float:
        if self.case_count == 0:
            return 1.0
        return self.passed_count / self.case_count


async def evaluate_cases(
    ai_service: StructuredGenerator, cases: tuple[EvaluationCase, ...]
) -> EvaluationReport:
    failed_cases: list[str] = []
    for case in cases:
        generated = await ai_service.generate(case.request, case.output_model)
        if not case.accepts(generated.value):
            failed_cases.append(case.name)
    return EvaluationReport(
        case_count=len(cases),
        passed_count=len(cases) - len(failed_cases),
        failed_cases=tuple(failed_cases),
    )

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvaluationCase(StrictModel):
    case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    family: str = Field(min_length=1)
    expected: Literal["benign", "malicious"]
    content: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class EvaluationSuite(StrictModel):
    schema_version: Literal[1] = 1
    description: str = Field(min_length=1)
    cases: list[EvaluationCase] = Field(min_length=1)

    @classmethod
    def from_path(cls, path: Path) -> EvaluationSuite:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


class CaseResult(StrictModel):
    case_id: str
    title: str
    family: str
    expected: Literal["benign", "malicious"]
    model: str
    content_intent: str
    semantic_risk: float = Field(ge=0.0, le=1.0)
    instruction_override_probability: float = Field(ge=0.0, le=1.0)
    capability_induction_probability: float = Field(ge=0.0, le=1.0)
    secret_exfiltration_probability: float = Field(ge=0.0, le=1.0)
    provenance_manipulation_probability: float = Field(ge=0.0, le=1.0)
    predicted_malicious: bool
    correct_at_threshold: bool
    scanner_findings: list[str] = Field(default_factory=list)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0.0)
    duration_ms: float = Field(ge=0.0)


class EvaluationSummary(StrictModel):
    cases: int
    benign_cases: int
    malicious_cases: int
    threshold: float
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int
    benign_scanner_warnings: int
    malicious_scanner_hits: int
    accuracy: float
    precision: float
    recall: float
    benign_mean_risk: float
    benign_max_risk: float
    malicious_mean_risk: float
    malicious_min_risk: float
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: float
    median_duration_ms: float


class EvaluationRun(StrictModel):
    schema_version: Literal[1] = 1
    benchmark: str
    benchmark_version: str
    timestamp_utc: str
    git_commit: str | None
    git_dirty: bool | None
    case_file: str
    configured_model: str
    methodology: str
    summary: EvaluationSummary
    cases: list[CaseResult]

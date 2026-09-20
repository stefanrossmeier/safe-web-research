from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictBenchmarkModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NetworkOrigin(StrEnum):
    MODEL = "model"
    SEARCH_RESULT = "search_result"


class NetworkRequest(StrictBenchmarkModel):
    url: HttpUrl
    origin: NetworkOrigin


class ActionSet(StrictBenchmarkModel):
    network_urls: list[HttpUrl] = Field(default_factory=list)
    secret_names: list[str] = Field(default_factory=list)
    shell_commands: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    extra_actions: list[str] = Field(default_factory=list)


class ModelProposal(StrictBenchmarkModel):
    network_requests: list[NetworkRequest] = Field(default_factory=list)
    secret_names: list[str] = Field(default_factory=list)
    shell_commands: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    extra_actions: list[str] = Field(default_factory=list)


class BenchmarkCase(StrictBenchmarkModel):
    case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    family: str = Field(min_length=1)
    adversarial: bool
    content: str
    resolver: dict[str, list[str]] = Field(default_factory=dict)
    known_evidence_ids: list[str] = Field(default_factory=list)
    required: ActionSet = Field(default_factory=ActionSet)
    forbidden: ActionSet = Field(default_factory=ActionSet)
    proposal: ModelProposal


class BenchmarkSuite(StrictBenchmarkModel):
    schema_version: Literal[1] = 1
    description: str = Field(min_length=1)
    cases: list[BenchmarkCase] = Field(min_length=1)

    @classmethod
    def from_path(cls, path: Path) -> BenchmarkSuite:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


class CaseOutcome(StrictBenchmarkModel):
    case_id: str
    architecture: str
    family: str
    adversarial: bool
    scanner_findings: list[str] = Field(default_factory=list)
    accepted: ActionSet = Field(default_factory=ActionSet)
    rejected: ActionSet = Field(default_factory=ActionSet)
    attack_success: bool
    task_completed: bool
    duration_ms: float = Field(ge=0.0)


class AggregateMetrics(StrictBenchmarkModel):
    architecture: str
    cases: int
    adversarial_cases: int
    benign_cases: int
    attack_successes: int
    attack_success_rate: float
    forbidden_network_actions: int
    forbidden_network_executed: int
    forbidden_network_execution_rate: float
    secret_exfiltration_actions: int
    secret_exfiltration_accepted: int
    secret_exfiltration_acceptance_rate: float
    shell_actions: int
    shell_actions_accepted: int
    shell_action_acceptance_rate: float
    invalid_provenance_actions: int
    invalid_provenance_accepted: int
    invalid_provenance_acceptance_rate: float
    action_smuggling_actions: int
    action_smuggling_accepted: int
    action_smuggling_acceptance_rate: float
    benign_tasks_completed: int
    benign_completion_rate: float
    benign_cases_with_security_warnings: int
    benign_security_warning_rate: float
    median_case_ms: float
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class BenchmarkRun(StrictBenchmarkModel):
    schema_version: Literal[1] = 1
    benchmark: str
    benchmark_version: str
    timestamp_utc: str
    git_commit: str | None
    git_dirty: bool | None
    case_file: str
    methodology: str
    results: list[AggregateMetrics]
    cases: list[CaseOutcome]

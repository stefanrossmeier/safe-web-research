from __future__ import annotations

from typing import Literal

from pydantic import Field

from examples.research_agent.models import ResearchAgentRun, ResearchCapability
from safe_web_research.domain.base import StrictModel


class AgentUsageCase(StrictModel):
    case_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    task: str = Field(min_length=1)
    expected_capabilities: list[ResearchCapability] = Field(min_length=1)
    expected_terms: list[str] = Field(default_factory=list)
    min_tool_calls: int = Field(default=1, ge=1)
    min_search_requests: int = Field(default=1, ge=1)
    min_sources: int = Field(default=1, ge=1)
    min_cited_sources: int = Field(default=1, ge=0)


class AgentUsageSuite(StrictModel):
    version: Literal["1"] = "1"
    cases: list[AgentUsageCase] = Field(min_length=1)


class AgentUsageCaseResult(StrictModel):
    case_id: str
    category: str
    outcome: Literal["pass", "fail", "error"]
    passed: bool
    failed_checks: list[str]
    answer_present: bool
    capability_pass: bool
    tool_call_pass: bool
    search_pass: bool
    source_pass: bool
    citation_pass: bool
    expected_terms_pass: bool
    expected_capabilities: list[str]
    capabilities_used: list[str]
    successful_tool_calls: int = Field(ge=0)
    rejected_tool_calls: int = Field(ge=0)
    search_requests: int = Field(ge=0)
    search_provider_errors: int = Field(ge=0)
    fetch_attempts: int = Field(ge=0)
    pages_fetched: int = Field(ge=0)
    unique_sources: int = Field(ge=0)
    cited_sources: int = Field(ge=0)
    expected_terms_found: int = Field(ge=0)
    expected_terms_total: int = Field(ge=0)
    agent_input_tokens: int = Field(ge=0)
    agent_output_tokens: int = Field(ge=0)
    research_input_tokens: int = Field(ge=0)
    research_output_tokens: int = Field(ge=0)
    agent_cost_usd: float = Field(ge=0.0)
    research_cost_usd: float = Field(ge=0.0)
    tracked_cost_usd: float = Field(ge=0.0)
    judgement_calls: int = Field(ge=0)
    redundant_research_calls_prevented: int = Field(ge=0)
    outer_model_seconds: float = Field(ge=0.0)
    research_tool_seconds: float = Field(ge=0.0)
    search_provider_seconds: float = Field(ge=0.0)
    fetch_seconds: float = Field(ge=0.0)
    research_llm_seconds: float = Field(ge=0.0)
    judgement_critical_path_seconds: float = Field(ge=0.0)
    unattributed_research_seconds: float = Field(ge=0.0)
    time_to_first_research_result_seconds: float | None = Field(default=None, ge=0.0)
    total_seconds: float = Field(ge=0.0)
    error_type: str | None = None
    error_message: str | None = None
    trace: ResearchAgentRun


class AgentUsageRun(StrictModel):
    benchmark: Literal["live-agent-usage"] = "live-agent-usage"
    benchmark_version: Literal["5"] = "5"
    timestamp_utc: str
    git_commit: str
    git_dirty: bool
    agent_model: str
    research_model: str
    research_profile: str
    case_file: str
    cases: list[AgentUsageCaseResult]
    passed_cases: int = Field(ge=0)
    error_cases: int = Field(ge=0)
    total_cases: int = Field(ge=0)
    total_tool_calls: int = Field(ge=0)
    total_search_requests: int = Field(ge=0)
    total_search_provider_errors: int = Field(ge=0)
    total_fetch_attempts: int = Field(ge=0)
    total_pages_fetched: int = Field(ge=0)
    total_judgement_calls: int = Field(ge=0)
    total_redundant_research_calls_prevented: int = Field(ge=0)
    total_agent_input_tokens: int = Field(ge=0)
    total_agent_output_tokens: int = Field(ge=0)
    total_research_input_tokens: int = Field(ge=0)
    total_research_output_tokens: int = Field(ge=0)
    total_agent_cost_usd: float = Field(ge=0.0)
    total_research_cost_usd: float = Field(ge=0.0)
    total_tracked_cost_usd: float = Field(ge=0.0)
    total_outer_model_seconds: float = Field(ge=0.0)
    total_research_tool_seconds: float = Field(ge=0.0)
    total_search_provider_seconds: float = Field(ge=0.0)
    total_fetch_seconds: float = Field(ge=0.0)
    total_research_llm_seconds: float = Field(ge=0.0)
    total_judgement_critical_path_seconds: float = Field(ge=0.0)
    total_unattributed_research_seconds: float = Field(ge=0.0)
    total_seconds: float = Field(ge=0.0)

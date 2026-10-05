from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from safe_web_research.domain import LLMUsage, ResearchUsage
from safe_web_research.domain.base import StrictModel


class ResearchCapability(StrEnum):
    """Bounded web-research profiles exposed to the example agent."""

    OPEN_WEB = "open_web"
    OFFICIAL_SOURCES = "official_sources"
    RECENT_WEB = "recent_web"
    REGIONAL_WEB = "regional_web"


class AgentDecision(StrictModel):
    """One small structured routing decision made by the outer research agent."""

    action: Literal["research", "finish"]
    question: str | None = Field(max_length=1_000)
    capability: ResearchCapability | None
    domains: list[str] = Field(max_length=5)
    freshness_days: int | None = Field(ge=1, le=90)
    language: str | None = Field(min_length=2, max_length=16)
    country: str | None = Field(min_length=2, max_length=16)


class SourceObservation(StrictModel):
    title: str = Field(max_length=500)
    url: str


class ClaimObservation(StrictModel):
    claim_id: str = Field(max_length=200)
    text: str = Field(max_length=1_000)
    verdict: str | None = Field(default=None, max_length=100)
    source_urls: list[str] = Field(default_factory=list, max_length=8)


class SearchCallObservation(StrictModel):
    """One actual call made to the configured search provider."""

    query: str = Field(max_length=2_000)
    domains: list[str] = Field(max_length=20)
    freshness_days: int | None
    language: str | None
    country: str | None
    seconds: float = Field(ge=0.0)
    ok: bool
    result_count: int = Field(ge=0)
    error_type: str | None = Field(default=None, max_length=200)
    error_message: str | None = Field(default=None, max_length=1_000)


class FetchCallObservation(StrictModel):
    """One actual safe-fetch attempt made while gathering web evidence."""

    url: str = Field(max_length=4_000)
    seconds: float = Field(ge=0.0)
    ok: bool
    bytes_fetched: int = Field(ge=0)
    error_type: str | None = Field(default=None, max_length=200)
    error_message: str | None = Field(default=None, max_length=1_000)


class ResearchLLMCallObservation(StrictModel):
    """One inner LLM call used by planning, synthesis, or verification."""

    purpose: str = Field(max_length=100)
    seconds: float = Field(ge=0.0)
    ok: bool
    model: str | None = Field(default=None, max_length=500)
    usage: LLMUsage | None = None
    error_type: str | None = Field(default=None, max_length=200)
    error_message: str | None = Field(default=None, max_length=1_000)


class JudgementCallObservation(StrictModel):
    """One semantic content-judgement call made for selected web evidence."""

    source_url: str = Field(max_length=4_000)
    seconds: float = Field(ge=0.0)
    ok: bool
    model: str | None = Field(default=None, max_length=500)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    error_type: str | None = Field(default=None, max_length=200)
    error_message: str | None = Field(default=None, max_length=1_000)


class ResearchObservation(StrictModel):
    """Bounded safe-web-research result passed back to the outer agent."""

    answer: str = Field(max_length=12_000)
    sources: list[SourceObservation] = Field(max_length=12)
    claims: list[ClaimObservation] = Field(max_length=12)
    incomplete_reasons: list[str] = Field(max_length=20)
    security_event_count: int = Field(ge=0)
    usage: ResearchUsage
    answer_chars_original: int = Field(ge=0)
    sources_total: int = Field(ge=0)
    claims_total: int = Field(ge=0)
    observation_truncated: bool


class AgentModelCall(StrictModel):
    step: int = Field(ge=1)
    purpose: Literal["decision", "final_answer"]
    seconds: float = Field(ge=0.0)
    decision: AgentDecision | None = None
    usage: LLMUsage
    model: str


class ResearchToolCall(StrictModel):
    step: int = Field(ge=1)
    capability: ResearchCapability
    question: str
    domains: list[str]
    freshness_days: int | None
    language: str | None
    country: str | None
    seconds: float = Field(ge=0.0)
    ok: bool
    error: str | None = None
    search_calls: list[SearchCallObservation] = Field(default_factory=list, max_length=8)
    fetch_calls: list[FetchCallObservation] = Field(default_factory=list, max_length=16)
    research_llm_calls: list[ResearchLLMCallObservation] = Field(
        default_factory=list,
        max_length=8,
    )
    judgement_calls: list[JudgementCallObservation] = Field(default_factory=list, max_length=8)
    observation: ResearchObservation | None = None


class ResearchAgentRun(StrictModel):
    """Full trace and measurements for one outer-agent run."""

    task: str
    agent_model: str
    research_model: str
    final_answer: str
    model_calls: list[AgentModelCall]
    tool_calls: list[ResearchToolCall]
    total_seconds: float = Field(ge=0.0)
    time_to_first_research_result_seconds: float | None = Field(default=None, ge=0.0)
    agent_input_tokens: int = Field(ge=0)
    agent_output_tokens: int = Field(ge=0)
    agent_cost_usd: float = Field(ge=0.0)
    research_input_tokens: int = Field(ge=0)
    research_output_tokens: int = Field(ge=0)
    research_cost_usd: float = Field(ge=0.0)
    judgement_calls: int = Field(ge=0)
    search_requests: int = Field(ge=0)
    search_provider_errors: int = Field(ge=0)
    fetch_attempts: int = Field(ge=0)
    pages_fetched: int = Field(ge=0)
    redundant_research_calls_prevented: int = Field(default=0, ge=0)
    tracked_cost_usd: float = Field(ge=0.0)
    error_type: str | None = None
    error_message: str | None = None
    failed_step: int | None = Field(default=None, ge=1)
    failed_purpose: Literal["decision", "final_answer"] | None = None

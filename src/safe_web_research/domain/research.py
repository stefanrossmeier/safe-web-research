from typing import Literal

from pydantic import Field

from safe_web_research.domain.base import StrictModel
from safe_web_research.domain.evidence import EvidenceChunk, Source
from safe_web_research.domain.security import SecurityEvent
from safe_web_research.domain.usage import ResearchBudget, ResearchUsage


class ResearchRequest(StrictModel):
    """Top-level request accepted by the research system."""

    api_version: Literal["v1"] = "v1"

    question: str = Field(min_length=1, max_length=10_000)

    budget: ResearchBudget = Field(default_factory=ResearchBudget)

    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)

    freshness_days: int | None = Field(default=None, ge=1)

    language: str | None = Field(default=None, min_length=2, max_length=16)
    country: str | None = Field(default=None, min_length=2, max_length=16)


class ResearchPlan(StrictModel):
    """Structured plan proposed by the research planner."""

    queries: list[str] = Field(min_length=1, max_length=20)


class Claim(StrictModel):
    """A factual claim backed by one or more pieces of evidence."""

    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)

    evidence_ids: list[str] = Field(min_length=1)

    confidence: float = Field(ge=0.0, le=1.0)


class Conflict(StrictModel):
    """Represents materially conflicting claims or source evidence."""

    conflict_id: str = Field(min_length=1)

    description: str = Field(min_length=1)

    claim_ids: list[str] = Field(min_length=2)


class ResearchResult(StrictModel):
    """Top-level result returned by the research system."""

    api_version: Literal["v1"] = "v1"

    answer: str

    claims: list[Claim] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    evidence: list[EvidenceChunk] = Field(default_factory=list)

    conflicts: list[Conflict] = Field(default_factory=list)

    security_events: list[SecurityEvent] = Field(default_factory=list)

    usage: ResearchUsage = Field(default_factory=ResearchUsage)

    incomplete_reasons: list[str] = Field(default_factory=list)

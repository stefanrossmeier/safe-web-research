from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator

from safe_web_research.domain.base import StrictModel
from safe_web_research.domain.domains import validate_domain
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

    @field_validator("allowed_domains", "blocked_domains")
    @classmethod
    def validate_domains(cls, values: list[str]) -> list[str]:
        return [validate_domain(value) for value in values]


class ResearchPlan(StrictModel):
    """Structured plan proposed by the research planner."""

    queries: list[str] = Field(min_length=1, max_length=20)


class Claim(StrictModel):
    """A factual claim backed by one or more pieces of evidence."""

    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)

    evidence_ids: list[str] = Field(min_length=1)

    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("evidence_ids")
    @classmethod
    def normalize_evidence_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = value.strip()

            if not cleaned:
                raise ValueError("evidence IDs must not be empty")

            if cleaned in seen:
                continue

            seen.add(cleaned)
            normalized.append(cleaned)

        if not normalized:
            raise ValueError("claim must contain at least one evidence ID")

        return normalized


class Conflict(StrictModel):
    """Represents materially conflicting claims or source evidence."""

    conflict_id: str = Field(min_length=1)

    description: str = Field(min_length=1)

    claim_ids: list[str] = Field(min_length=2)


class ClaimSupport(StrEnum):
    """Semantic support verdict for one synthesized claim."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"


class ClaimVerification(StrictModel):
    """Independent semantic check of a claim against its cited evidence."""

    claim_id: str = Field(min_length=1)
    verdict: ClaimSupport
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence_ids: list[str]
    explanation: str = Field(min_length=1, max_length=2_000)

    @field_validator("supporting_evidence_ids")
    @classmethod
    def normalize_supporting_evidence_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned = value.strip()

            if not cleaned:
                raise ValueError("supporting evidence IDs must not be empty")

            if cleaned in seen:
                continue

            seen.add(cleaned)
            normalized.append(cleaned)

        return normalized


class VerificationDraft(StrictModel):
    """Structured verifier output for all synthesized claims."""

    verifications: list[ClaimVerification] = Field(min_length=1, max_length=100)


class SynthesisDraft(StrictModel):
    """Structured answer draft proposed from already collected evidence."""

    answer: str = Field(min_length=1)

    claims: list[Claim] = Field(
        min_length=1,
        max_length=100,
    )

    conflicts: list[Conflict] = Field(
        max_length=50,
    )


class ResearchResult(StrictModel):
    """Top-level result returned by the research system."""

    api_version: Literal["v1"] = "v1"

    answer: str

    claims: list[Claim] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    evidence: list[EvidenceChunk] = Field(default_factory=list)

    conflicts: list[Conflict] = Field(default_factory=list)

    claim_verifications: list[ClaimVerification] = Field(default_factory=list)

    security_events: list[SecurityEvent] = Field(default_factory=list)

    usage: ResearchUsage = Field(default_factory=ResearchUsage)

    incomplete_reasons: list[str] = Field(default_factory=list)


class EvidenceBundle(StrictModel):
    """Evidence collected before language-model synthesis."""

    queries: list[str] = Field(default_factory=list)

    sources: list[Source] = Field(default_factory=list)
    evidence: list[EvidenceChunk] = Field(default_factory=list)

    security_events: list[SecurityEvent] = Field(default_factory=list)

    usage: ResearchUsage = Field(default_factory=ResearchUsage)

    incomplete_reasons: list[str] = Field(default_factory=list)

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from safe_web_research.domain import (
    EvidenceChunk,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    Source,
)


class ContentIntent(StrEnum):
    """How untrusted content relates to a model that is consuming it."""

    ORDINARY = "ordinary_content"
    BENIGN_AI_DISCUSSION = "benign_ai_discussion"
    OPERATIVE_MODEL_INSTRUCTION = "operative_model_instruction"
    UNCLEAR = "unclear"


class ContentJudgementMode(StrEnum):
    """Trusted runtime policy for semantic content judgement."""

    OFF = "off"
    OBSERVE = "observe"


@dataclass(frozen=True, slots=True)
class DecisionUsage:
    """Provider-reported resources consumed by one decision request."""

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.input_tokens < 0:
            raise ValueError("input_tokens must not be negative")
        if self.output_tokens < 0:
            raise ValueError("output_tokens must not be negative")
        if self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must not be negative")

    def __add__(self, other: "DecisionUsage") -> "DecisionUsage":
        return DecisionUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            estimated_cost_usd=self.estimated_cost_usd + other.estimated_cost_usd,
        )


@dataclass(frozen=True, slots=True)
class SecurityJudgementInput:
    """Minimal public-web state supplied to a semantic security judge."""

    source_id: str
    source_url: str
    content: str
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class SecurityAssessment:
    """Typed, provider-neutral semantic security signals for one source."""

    source_id: str
    source_url: str
    model: str
    content_intent: ContentIntent
    content_intent_probabilities: dict[ContentIntent, float]
    instruction_override_probability: float
    capability_induction_probability: float
    secret_exfiltration_probability: float
    provenance_manipulation_probability: float
    input_truncated: bool
    usage: DecisionUsage

    def __post_init__(self) -> None:
        expected = set(ContentIntent)
        if set(self.content_intent_probabilities) != expected:
            raise ValueError("content_intent_probabilities must contain every ContentIntent")
        for probability in (
            *self.content_intent_probabilities.values(),
            self.instruction_override_probability,
            self.capability_induction_probability,
            self.secret_exfiltration_probability,
            self.provenance_manipulation_probability,
        ):
            if not 0.0 <= probability <= 1.0:
                raise ValueError("security probabilities must be between zero and one")

    @property
    def semantic_risk(self) -> float:
        """Return a deterministic aggregate risk signal owned by trusted code."""

        return max(
            self.content_intent_probabilities[ContentIntent.OPERATIVE_MODEL_INSTRUCTION],
            self.instruction_override_probability,
            self.capability_induction_probability,
            self.secret_exfiltration_probability,
            self.provenance_manipulation_probability,
        )


class ContentJudgementError(RuntimeError):
    """Base class for semantic content-judgement failures."""


class ContentJudgementConfigurationError(ContentJudgementError):
    """Raised when a content judge is configured incorrectly."""


class ContentJudgementAuthenticationError(ContentJudgementError):
    """Raised when the decision provider rejects authentication."""


class ContentJudgementRateLimitError(ContentJudgementError):
    """Raised when the decision provider rate-limits the request."""


class ContentJudgementRequestError(ContentJudgementError):
    """Raised when the decision provider rejects a request."""


class ContentJudgementResponseError(ContentJudgementError):
    """Raised when the decision provider returns an invalid response."""


class ContentJudgementUnavailableError(ContentJudgementError):
    """Raised when the decision provider cannot be reached or is unavailable."""


class ContentSecurityJudge(Protocol):
    """Provider-neutral semantic judge for already-fetched untrusted content."""

    async def assess(self, content: SecurityJudgementInput) -> SecurityAssessment:
        """Return typed semantic security signals without granting authority."""
        ...


@dataclass(frozen=True, slots=True)
class ContentJudgementPolicy:
    """Trusted policy for bounded semantic judgement of selected evidence."""

    mode: ContentJudgementMode = ContentJudgementMode.OFF
    event_threshold: float = 0.85
    max_calls: int = 4
    max_chars_per_source: int = 64_000
    concurrency: int = 4

    def __post_init__(self) -> None:
        if not 0.0 <= self.event_threshold <= 1.0:
            raise ValueError("event_threshold must be between zero and one")
        if self.max_calls < 0:
            raise ValueError("max_calls must not be negative")
        if self.max_chars_per_source <= 0:
            raise ValueError("max_chars_per_source must be greater than zero")
        if self.concurrency <= 0:
            raise ValueError("concurrency must be greater than zero")


@dataclass(frozen=True, slots=True)
class ContentJudgementReport:
    """Observability result from a bounded semantic-judgement pass."""

    events: tuple[SecurityEvent, ...] = ()
    assessments: tuple[SecurityAssessment, ...] = ()
    usage: DecisionUsage = DecisionUsage()
    calls_attempted: int = 0
    skipped_sources: int = 0


class ContentJudgementObserver:
    """Observe selected evidence semantically without changing evidence authority."""

    def __init__(
        self,
        judge: ContentSecurityJudge | None = None,
        *,
        policy: ContentJudgementPolicy | None = None,
    ) -> None:
        self._policy = policy or ContentJudgementPolicy()
        self._judge = judge
        if self._policy.mode is ContentJudgementMode.OBSERVE and self._judge is None:
            raise ContentJudgementConfigurationError("observe mode requires a ContentSecurityJudge")

    async def observe(
        self,
        sources: Sequence[Source],
        evidence: Sequence[EvidenceChunk],
    ) -> ContentJudgementReport:
        """Assess selected evidence by source and emit observability events only."""

        if self._policy.mode is ContentJudgementMode.OFF or not sources or not evidence:
            return ContentJudgementReport()

        judge = self._judge
        assert judge is not None

        chunks_by_source: dict[str, list[EvidenceChunk]] = {}
        for chunk in evidence:
            chunks_by_source.setdefault(chunk.source_id, []).append(chunk)

        candidates: list[tuple[Source, list[EvidenceChunk]]] = []
        for source in sources:
            chunks = chunks_by_source.get(source.source_id)
            if chunks:
                candidates.append((source, chunks))

        selected = candidates[: self._policy.max_calls]
        skipped_sources = max(0, len(candidates) - len(selected))
        events: list[SecurityEvent] = []
        if skipped_sources:
            events.append(
                SecurityEvent(
                    event_type=SecurityEventType.RESOURCE_LIMIT,
                    severity=SecuritySeverity.INFO,
                    message="Semantic content judgement call limit reached.",
                    source="content_judgement",
                    metadata={
                        "component": "content_judgement",
                        "max_calls": self._policy.max_calls,
                        "skipped_sources": skipped_sources,
                    },
                )
            )

        semaphore = asyncio.Semaphore(self._policy.concurrency)

        async def assess_one(
            source: Source,
            chunks: list[EvidenceChunk],
        ) -> SecurityAssessment | Exception:
            content, truncated = build_judgement_content(
                chunks,
                max_chars=self._policy.max_chars_per_source,
            )
            judgement_input = SecurityJudgementInput(
                source_id=source.source_id,
                source_url=str(source.url),
                content=content,
                truncated=truncated,
            )
            try:
                async with semaphore:
                    return await judge.assess(judgement_input)
            except Exception as exc:
                return exc

        results = await asyncio.gather(*(assess_one(source, chunks) for source, chunks in selected))

        assessments: list[SecurityAssessment] = []
        usage = DecisionUsage()
        for (source, _), result in zip(selected, results, strict=True):
            if isinstance(result, Exception):
                events.append(
                    SecurityEvent(
                        event_type=SecurityEventType.CONTENT_JUDGEMENT_ERROR,
                        severity=SecuritySeverity.WARNING,
                        message="Semantic content judgement failed; evidence was left unchanged.",
                        source=str(source.url),
                        metadata={
                            "error_type": type(result).__name__,
                            "source_id": source.source_id,
                        },
                    )
                )
                continue

            assessments.append(result)
            usage += result.usage
            if result.semantic_risk >= self._policy.event_threshold:
                events.append(self._risk_event(result))

        return ContentJudgementReport(
            events=tuple(events),
            assessments=tuple(assessments),
            usage=usage,
            calls_attempted=len(selected),
            skipped_sources=skipped_sources,
        )

    @staticmethod
    def _risk_event(assessment: SecurityAssessment) -> SecurityEvent:
        return SecurityEvent(
            event_type=SecurityEventType.SEMANTIC_CONTENT_RISK,
            severity=SecuritySeverity.WARNING,
            message="Semantic content-risk judgement exceeded the configured threshold.",
            source=assessment.source_url,
            metadata={
                "judge_model": assessment.model,
                "source_id": assessment.source_id,
                "semantic_risk": assessment.semantic_risk,
                "content_intent": assessment.content_intent.value,
                "operative_instruction_probability": assessment.content_intent_probabilities[
                    ContentIntent.OPERATIVE_MODEL_INSTRUCTION
                ],
                "instruction_override_probability": assessment.instruction_override_probability,
                "capability_induction_probability": assessment.capability_induction_probability,
                "secret_exfiltration_probability": assessment.secret_exfiltration_probability,
                "provenance_manipulation_probability": (
                    assessment.provenance_manipulation_probability
                ),
                "input_truncated": assessment.input_truncated,
            },
        )


def build_judgement_content(
    chunks: Sequence[EvidenceChunk],
    *,
    max_chars: int,
) -> tuple[str, bool]:
    """Build a deterministic bounded sample spanning all selected chunks for a source."""

    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")
    if not chunks:
        return "", False

    ordered = sorted(chunks, key=lambda item: (item.position, item.chunk_id))
    rendered = [f"[{chunk.chunk_id}]\n{chunk.text}" for chunk in ordered]
    full = "\n\n".join(rendered)
    if len(full) <= max_chars:
        return full, False

    separator_chars = 2 * (len(rendered) - 1)
    usable = max(1, max_chars - separator_chars)
    per_chunk = max(1, usable // len(rendered))
    sampled = [_sample_head_tail(item, per_chunk) for item in rendered]
    bounded = "\n\n".join(sampled)[:max_chars]
    return bounded, True


def _sample_head_tail(text: str, budget: int) -> str:
    if len(text) <= budget:
        return text
    if budget <= 5:
        return text[:budget]

    marker = "\n...\n"
    remaining = budget - len(marker)
    head = (remaining + 1) // 2
    tail = remaining - head
    if tail == 0:
        return text[:head] + marker
    return text[:head] + marker + text[-tail:]

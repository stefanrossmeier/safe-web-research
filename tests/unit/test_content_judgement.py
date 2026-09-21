import asyncio
from datetime import UTC, datetime

import pytest

from safe_web_research.domain import EvidenceChunk, SecurityEventType, Source
from safe_web_research.security.judgement import (
    ContentIntent,
    ContentJudgementConfigurationError,
    ContentJudgementMode,
    ContentJudgementObserver,
    ContentJudgementPolicy,
    DecisionUsage,
    SecurityAssessment,
    SecurityJudgementInput,
    build_judgement_content,
)


def _source(source_id: str = "source-1") -> Source:
    return Source(
        source_id=source_id,
        url=f"https://example.com/{source_id}",
        title="Example",
        provider="test",
        retrieved_at=datetime.now(UTC),
        content_hash="a" * 64,
    )


def _chunk(source_id: str, position: int, text: str) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=f"{source_id}-chunk-{position}",
        source_id=source_id,
        text=text,
        position=position,
    )


def _assessment(content: SecurityJudgementInput, risk: float) -> SecurityAssessment:
    return SecurityAssessment(
        source_id=content.source_id,
        source_url=content.source_url,
        model="typesafe/jev-1.13-20260917",
        content_intent=(
            ContentIntent.OPERATIVE_MODEL_INSTRUCTION if risk >= 0.5 else ContentIntent.ORDINARY
        ),
        content_intent_probabilities={
            ContentIntent.ORDINARY: 1.0 - risk,
            ContentIntent.BENIGN_AI_DISCUSSION: 0.0,
            ContentIntent.OPERATIVE_MODEL_INSTRUCTION: risk,
            ContentIntent.UNCLEAR: 0.0,
        },
        instruction_override_probability=risk,
        capability_induction_probability=0.1,
        secret_exfiltration_probability=0.2,
        provenance_manipulation_probability=0.3,
        input_truncated=content.truncated,
        usage=DecisionUsage(input_tokens=100, output_tokens=5, estimated_cost_usd=0.001),
    )


class _FakeJudge:
    def __init__(self, risks: dict[str, float], *, delay: float = 0.0) -> None:
        self.risks = risks
        self.delay = delay
        self.inputs: list[SecurityJudgementInput] = []
        self.active = 0
        self.max_active = 0

    async def assess(self, content: SecurityJudgementInput) -> SecurityAssessment:
        self.inputs.append(content)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            return _assessment(content, self.risks[content.source_id])
        finally:
            self.active -= 1


class _FailingJudge:
    async def assess(self, content: SecurityJudgementInput) -> SecurityAssessment:
        raise RuntimeError(f"provider failed for {content.source_id}")


def test_security_assessment_risk_is_deterministic_maximum() -> None:
    content = SecurityJudgementInput(
        source_id="s",
        source_url="https://example.com/",
        content="x",
    )
    assessment = _assessment(content, 0.72)
    assert assessment.semantic_risk == 0.72


def test_build_judgement_content_preserves_all_content_when_within_limit() -> None:
    chunks = [_chunk("s", 1, "second"), _chunk("s", 0, "first")]
    content, truncated = build_judgement_content(chunks, max_chars=1000)
    assert truncated is False
    assert content.index("s-chunk-0") < content.index("s-chunk-1")
    assert "first" in content
    assert "second" in content


def test_build_judgement_content_samples_head_and_tail_across_chunks() -> None:
    chunks = [
        _chunk("s", 0, "HEAD-A" + "x" * 300 + "TAIL-A"),
        _chunk("s", 1, "HEAD-B" + "y" * 300 + "TAIL-B"),
    ]
    content, truncated = build_judgement_content(chunks, max_chars=160)
    assert truncated is True
    assert len(content) <= 160
    assert "HEAD-A" in content and "TAIL-A" in content
    assert "HEAD-B" in content and "TAIL-B" in content


def test_observe_mode_requires_a_judge() -> None:
    with pytest.raises(ContentJudgementConfigurationError):
        ContentJudgementObserver(policy=ContentJudgementPolicy(mode=ContentJudgementMode.OBSERVE))


@pytest.mark.asyncio
async def test_off_mode_does_not_call_judge() -> None:
    judge = _FakeJudge({"source-1": 1.0})
    observer = ContentJudgementObserver(
        judge,
        policy=ContentJudgementPolicy(mode=ContentJudgementMode.OFF),
    )
    report = await observer.observe([_source()], [_chunk("source-1", 0, "hostile")])
    assert judge.inputs == []
    assert report.calls_attempted == 0
    assert report.events == ()


@pytest.mark.asyncio
async def test_observer_groups_selected_chunks_by_source_and_emits_risk_event() -> None:
    judge = _FakeJudge({"source-1": 0.97, "source-2": 0.10})
    observer = ContentJudgementObserver(
        judge,
        policy=ContentJudgementPolicy(
            mode=ContentJudgementMode.OBSERVE,
            event_threshold=0.85,
            max_calls=4,
            max_chars_per_source=1000,
        ),
    )
    sources = [_source("source-1"), _source("source-2")]
    evidence = [
        _chunk("source-1", 0, "one"),
        _chunk("source-1", 1, "two"),
        _chunk("source-2", 0, "three"),
    ]

    report = await observer.observe(sources, evidence)

    assert report.calls_attempted == 2
    assert len(judge.inputs) == 2
    assert "one" in judge.inputs[0].content and "two" in judge.inputs[0].content
    assert judge.inputs[0].source_id == "source-1"
    assert report.usage.input_tokens == 200
    assert report.usage.output_tokens == 10
    assert report.usage.estimated_cost_usd == pytest.approx(0.002)
    risk_events = [
        event
        for event in report.events
        if event.event_type is SecurityEventType.SEMANTIC_CONTENT_RISK
    ]
    assert len(risk_events) == 1
    assert risk_events[0].source == "https://example.com/source-1"
    assert risk_events[0].metadata["semantic_risk"] == pytest.approx(0.97)
    assert "hostile" not in risk_events[0].metadata


@pytest.mark.asyncio
async def test_observer_converts_judge_failure_to_event_and_keeps_running() -> None:
    observer = ContentJudgementObserver(
        _FailingJudge(),
        policy=ContentJudgementPolicy(mode=ContentJudgementMode.OBSERVE),
    )
    report = await observer.observe([_source()], [_chunk("source-1", 0, "data")])
    assert len(report.events) == 1
    assert report.events[0].event_type is SecurityEventType.CONTENT_JUDGEMENT_ERROR
    assert "evidence was left unchanged" in report.events[0].message
    assert report.assessments == ()


@pytest.mark.asyncio
async def test_observer_bounds_calls_and_reports_skipped_sources() -> None:
    judge = _FakeJudge({f"source-{i}": 0.1 for i in range(4)})
    observer = ContentJudgementObserver(
        judge,
        policy=ContentJudgementPolicy(
            mode=ContentJudgementMode.OBSERVE,
            max_calls=2,
        ),
    )
    sources = [_source(f"source-{i}") for i in range(4)]
    evidence = [_chunk(source.source_id, 0, "data") for source in sources]
    report = await observer.observe(sources, evidence)
    assert report.calls_attempted == 2
    assert report.skipped_sources == 2
    assert len(judge.inputs) == 2
    assert any(event.event_type is SecurityEventType.RESOURCE_LIMIT for event in report.events)


@pytest.mark.asyncio
async def test_observer_respects_concurrency_limit() -> None:
    judge = _FakeJudge({f"source-{i}": 0.1 for i in range(4)}, delay=0.01)
    observer = ContentJudgementObserver(
        judge,
        policy=ContentJudgementPolicy(
            mode=ContentJudgementMode.OBSERVE,
            max_calls=4,
            concurrency=2,
        ),
    )
    sources = [_source(f"source-{i}") for i in range(4)]
    evidence = [_chunk(source.source_id, 0, "data") for source in sources]
    await observer.observe(sources, evidence)
    assert judge.max_active == 2

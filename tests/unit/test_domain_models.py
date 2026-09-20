from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from safe_web_research.domain import (
    Claim,
    EvidenceChunk,
    ResearchBudget,
    ResearchRequest,
    ResearchResult,
    SearchRequest,
    SearchResult,
    Source,
)


def test_research_request_defaults() -> None:
    request = ResearchRequest(question="What changed in Python 3.15?")

    assert request.api_version == "v1"
    assert request.question == "What changed in Python 3.15?"
    assert request.budget.max_searches == 10
    assert request.budget.max_fetch_attempts == 40
    assert request.budget.max_pages == 20
    assert request.budget.max_total_bytes == 50_000_000
    assert request.budget.max_llm_calls == 10
    assert request.budget.max_input_tokens == 500_000
    assert request.budget.max_output_tokens == 50_000
    assert request.allowed_domains == []
    assert request.blocked_domains == []


def test_domain_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest.model_validate(
            {
                "question": "Test question",
                "unexpected": "must not be silently accepted",
            }
        )


def test_empty_question_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(question="")


def test_invalid_budget_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ResearchBudget(max_searches=-1)


def test_budget_absolute_ceiling_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ResearchBudget(max_input_tokens=5_000_001)


def test_search_request_validates_result_limit() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(
            query="test query",
            max_results=1000,
        )


def test_search_result_requires_http_url() -> None:
    with pytest.raises(ValidationError):
        SearchResult.model_validate(
            {
                "result_id": "result-1",
                "url": "file:///etc/passwd",
                "title": "Unsafe result",
                "snippet": "This must not validate.",
                "rank": 1,
                "provider": "fake",
            }
        )


def test_research_result_preserves_evidence_provenance() -> None:
    now = datetime.now(UTC)

    source = Source(
        source_id="source-1",
        url="https://example.com/article",
        title="Example",
        provider="fake",
        retrieved_at=now,
        content_hash="a" * 64,
    )

    evidence = EvidenceChunk(
        chunk_id="evidence-1",
        source_id="source-1",
        text="Python 3.15 contains an example change.",
        position=0,
    )

    claim = Claim(
        claim_id="claim-1",
        text="Python 3.15 contains an example change.",
        evidence_ids=["evidence-1"],
        confidence=0.9,
    )

    result = ResearchResult(
        answer="Example answer.",
        claims=[claim],
        sources=[source],
        evidence=[evidence],
    )

    assert result.claims[0].evidence_ids == ["evidence-1"]
    assert result.evidence[0].source_id == "source-1"
    assert str(result.sources[0].url) == "https://example.com/article"


def test_research_result_serializes_to_json() -> None:
    result = ResearchResult(answer="No evidence gathered yet.")

    serialized = result.model_dump_json()

    assert '"api_version":"v1"' in serialized
    assert '"answer":"No evidence gathered yet."' in serialized

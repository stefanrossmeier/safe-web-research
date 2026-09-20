import json
from datetime import UTC, datetime

import pytest

from safe_web_research.domain import (
    EvidenceChunk,
    ExtractedDocument,
    FetchedDocument,
    LLMResponse,
    LLMUsage,
    ResearchBudget,
    ResearchRequest,
    SearchResult,
    Source,
)
from safe_web_research.extraction import FakeExtractor
from safe_web_research.fetch import FakeFetcher
from safe_web_research.llm import FakeLLMProvider
from safe_web_research.research import (
    EvidenceGatherer,
    ResearchPlanner,
    ResearchService,
    ResearchSynthesizer,
    ResearchVerifier,
)
from safe_web_research.search import FakeSearchProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_service_verifies_synthesized_claims() -> None:
    url = "https://example.com/article"
    query = "Python 3.15 encoding changes"

    search = FakeSearchProvider(
        {
            query: [
                SearchResult(
                    result_id="result-1",
                    url=url,
                    title="Example",
                    snippet="Example",
                    rank=1,
                    provider="fake",
                )
            ]
        }
    )

    document = FetchedDocument(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/plain",
        body=b"Python 3.15 uses UTF-8 by default.",
    )

    source = Source(
        source_id="source-1",
        url=url,
        title="Example",
        provider="fake",
        retrieved_at=datetime(
            2026,
            9,
            20,
            tzinfo=UTC,
        ),
        content_hash="1" * 64,
    )

    extractor = FakeExtractor(
        {
            url: ExtractedDocument(
                source=source,
                chunks=[
                    EvidenceChunk(
                        chunk_id="evidence-1",
                        source_id="source-1",
                        text="Python 3.15 uses UTF-8 by default.",
                        position=0,
                    )
                ],
            )
        }
    )

    llm = FakeLLMProvider(
        [
            LLMResponse(
                content=json.dumps({"queries": [query]}),
                model="fake-planner",
                usage=LLMUsage(
                    input_tokens=20,
                    output_tokens=10,
                ),
            ),
            LLMResponse(
                content=json.dumps(
                    {
                        "answer": "Python 3.15 uses UTF-8 by default.",
                        "claims": [
                            {
                                "claim_id": "claim-1",
                                "text": "Python 3.15 uses UTF-8 by default.",
                                "evidence_ids": ["evidence-1"],
                                "confidence": 0.95,
                            }
                        ],
                        "conflicts": [],
                    }
                ),
                model="fake-synth",
                usage=LLMUsage(
                    input_tokens=80,
                    output_tokens=30,
                ),
            ),
            LLMResponse(
                content=json.dumps(
                    {
                        "verifications": {
                            "Q1": {
                                "verdict": "supported",
                                "confidence": 0.99,
                                "supporting_evidence_ids": ["E1"],
                                "explanation": ("The evidence directly supports the claim."),
                            }
                        }
                    }
                ),
                model="fake-verifier",
                usage=LLMUsage(
                    input_tokens=60,
                    output_tokens=20,
                ),
            ),
        ]
    )

    service = ResearchService(
        ResearchPlanner(llm),
        EvidenceGatherer(
            search,
            FakeFetcher({url: document}),
            extractor,
        ),
        ResearchSynthesizer(llm),
        ResearchVerifier(llm),
    )

    result = await service.research(
        ResearchRequest(
            question="What changed in Python 3.15 encoding?",
            budget=ResearchBudget(
                max_searches=2,
                max_pages=2,
                max_llm_calls=3,
                max_input_tokens=10_000,
                max_output_tokens=50_000,
            ),
        )
    )

    assert result.answer
    assert len(result.claim_verifications) == 1
    assert result.claim_verifications[0].claim_id == "claim-1"
    assert result.claim_verifications[0].supporting_evidence_ids == ["evidence-1"]
    assert result.claim_verifications[0].verdict == "supported"
    assert result.usage.llm_calls == 3
    assert result.usage.input_tokens == 160
    assert result.usage.output_tokens == 60
    assert result.incomplete_reasons == []
    assert llm.requests[1].max_output_tokens == 16_000
    assert llm.requests[2].max_output_tokens == 16_000


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_service_surfaces_unsupported_claims() -> None:
    url = "https://example.com/article"

    search = FakeSearchProvider(
        {
            "question": [
                SearchResult(
                    result_id="result-1",
                    url=url,
                    title="Example",
                    snippet="Example",
                    rank=1,
                    provider="fake",
                )
            ]
        }
    )

    source = Source(
        source_id="source-1",
        url=url,
        title="Example",
        provider="fake",
        retrieved_at=datetime(
            2026,
            9,
            20,
            tzinfo=UTC,
        ),
        content_hash="2" * 64,
    )

    llm = FakeLLMProvider(
        [
            LLMResponse(
                content=json.dumps({"queries": ["question"]}),
                model="fake-planner",
            ),
            LLMResponse(
                content=json.dumps(
                    {
                        "answer": "Unsupported claim.",
                        "claims": [
                            {
                                "claim_id": "claim-1",
                                "text": "Unsupported claim.",
                                "evidence_ids": ["evidence-1"],
                                "confidence": 0.8,
                            }
                        ],
                        "conflicts": [],
                    }
                ),
                model="fake-synth",
            ),
            LLMResponse(
                content=json.dumps(
                    {
                        "verifications": {
                            "Q1": {
                                "verdict": "unsupported",
                                "confidence": 0.95,
                                "supporting_evidence_ids": [],
                                "explanation": "The evidence does not establish it.",
                            }
                        }
                    }
                ),
                model="fake-verifier",
            ),
        ]
    )

    service = ResearchService(
        ResearchPlanner(llm),
        EvidenceGatherer(
            search,
            FakeFetcher(
                {
                    url: FetchedDocument(
                        requested_url=url,
                        final_url=url,
                        status_code=200,
                        content_type="text/plain",
                        body=b"Different fact.",
                    )
                }
            ),
            FakeExtractor(
                {
                    url: ExtractedDocument(
                        source=source,
                        chunks=[
                            EvidenceChunk(
                                chunk_id="evidence-1",
                                source_id="source-1",
                                text="Different fact.",
                                position=0,
                            )
                        ],
                    )
                }
            ),
        ),
        ResearchSynthesizer(llm),
        ResearchVerifier(llm),
    )

    result = await service.research(
        ResearchRequest(
            question="question",
            budget=ResearchBudget(
                max_searches=1,
                max_pages=1,
                max_llm_calls=3,
                max_output_tokens=3_000,
            ),
        )
    )

    assert result.claim_verifications[0].claim_id == "claim-1"
    assert result.claim_verifications[0].supporting_evidence_ids == []
    assert result.claim_verifications[0].verdict == "unsupported"
    assert "claim_support_issues" in result.incomplete_reasons

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
from safe_web_research.extraction import (
    FakeExtractor,
)
from safe_web_research.fetch import (
    FakeFetcher,
)
from safe_web_research.llm import (
    FakeLLMProvider,
)
from safe_web_research.research import (
    EvidenceGatherer,
    ResearchPlanner,
    ResearchService,
    ResearchSynthesizer,
)
from safe_web_research.search import (
    FakeSearchProvider,
)


def _service(
    *,
    llm_responses: list[LLMResponse],
    search_query: str,
) -> tuple[
    ResearchService,
    FakeLLMProvider,
    FakeSearchProvider,
    FakeFetcher,
]:
    url = "https://example.com/article"

    search = FakeSearchProvider(
        {
            search_query: [
                SearchResult(
                    result_id="result-1",
                    url=url,
                    title="Example",
                    snippet="Example snippet",
                    rank=1,
                    provider="fake",
                )
            ]
        }
    )

    fetched = FetchedDocument(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/plain",
        body=(b"Python 3.15 uses UTF-8 by default."),
    )

    fetcher = FakeFetcher(
        {
            url: fetched,
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
                        text=("Python 3.15 uses UTF-8 by default."),
                        position=0,
                    )
                ],
            )
        }
    )

    llm = FakeLLMProvider(llm_responses)

    gatherer = EvidenceGatherer(
        search,
        fetcher,
        extractor,
    )

    service = ResearchService(
        ResearchPlanner(llm),
        gatherer,
        ResearchSynthesizer(llm),
    )

    return (
        service,
        llm,
        search,
        fetcher,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_service_runs_planner_gatherer_and_synthesizer() -> None:
    planner_response = LLMResponse(
        content=json.dumps({"queries": [("Python 3.15 encoding changes")]}),
        model="fake-planner",
        usage=LLMUsage(
            input_tokens=20,
            output_tokens=10,
            estimated_cost_usd=0.001,
        ),
    )

    synthesis_response = LLMResponse(
        content=json.dumps(
            {
                "answer": ("Python 3.15 uses UTF-8 by default."),
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "text": ("Python 3.15 uses UTF-8 by default."),
                        "evidence_ids": ["evidence-1"],
                        "confidence": 0.95,
                    }
                ],
                "conflicts": [],
            }
        ),
        model="fake-synth",
        usage=LLMUsage(
            input_tokens=100,
            output_tokens=40,
            estimated_cost_usd=0.002,
        ),
    )

    (
        service,
        llm,
        search,
        fetcher,
    ) = _service(
        llm_responses=[
            planner_response,
            synthesis_response,
        ],
        search_query=("Python 3.15 encoding changes"),
    )

    result = await service.research(
        ResearchRequest(
            question=("What changed in Python 3.15 encoding?"),
            budget=ResearchBudget(
                max_searches=2,
                max_pages=2,
                max_llm_calls=2,
                max_input_tokens=10_000,
                max_output_tokens=2_000,
            ),
        )
    )

    assert result.answer == ("Python 3.15 uses UTF-8 by default.")

    assert result.claims[0].evidence_ids == ["evidence-1"]

    assert len(result.sources) == 1
    assert len(result.evidence) == 1

    assert result.incomplete_reasons == []

    assert len(llm.requests) == 2

    assert [request.query for request in search.requests] == [("Python 3.15 encoding changes")]

    assert len(fetcher.requests) == 1

    assert result.usage.search_requests == 1

    assert result.usage.fetch_attempts == 1

    assert result.usage.pages_fetched == 1

    assert result.usage.bytes_fetched > 0

    assert result.usage.llm_calls == 2

    assert result.usage.input_tokens == 120

    assert result.usage.output_tokens == 50

    assert result.usage.estimated_cost_usd == pytest.approx(0.003)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_service_preserves_single_llm_call_for_synthesis() -> None:
    synthesis_response = LLMResponse(
        content=json.dumps(
            {
                "answer": ("Python 3.15 uses UTF-8 by default."),
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "text": ("Python 3.15 uses UTF-8 by default."),
                        "evidence_ids": ["evidence-1"],
                        "confidence": 0.9,
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
    )

    question = "What changed in Python 3.15 encoding?"

    (
        service,
        llm,
        search,
        _,
    ) = _service(
        llm_responses=[synthesis_response],
        search_query=question,
    )

    result = await service.research(
        ResearchRequest(
            question=question,
            budget=ResearchBudget(
                max_searches=1,
                max_pages=1,
                max_llm_calls=1,
                max_input_tokens=10_000,
                max_output_tokens=1_000,
            ),
        )
    )

    assert result.answer

    assert len(llm.requests) == 1

    assert [request.query for request in search.requests] == [question]

    assert "planner_skipped_llm_budget" in result.incomplete_reasons

    assert result.usage.llm_calls == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_service_does_not_synthesize_without_evidence() -> None:
    planner_response = LLMResponse(
        content=('{"queries":["nothing here"]}'),
        model="fake-planner",
        usage=LLMUsage(
            input_tokens=10,
            output_tokens=5,
        ),
    )

    llm = FakeLLMProvider([planner_response])

    search = FakeSearchProvider({"nothing here": []})

    service = ResearchService(
        ResearchPlanner(llm),
        EvidenceGatherer(
            search,
            FakeFetcher(),
            FakeExtractor(),
        ),
        ResearchSynthesizer(llm),
    )

    result = await service.research(
        ResearchRequest(
            question="Unknown question",
            budget=ResearchBudget(
                max_searches=1,
                max_pages=1,
                max_llm_calls=2,
            ),
        )
    )

    assert result.answer == ""
    assert result.claims == []

    assert "no_evidence" in result.incomplete_reasons

    assert len(llm.requests) == 1

    assert result.usage.llm_calls == 1

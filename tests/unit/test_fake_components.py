from datetime import UTC, datetime

import pytest

from safe_web_research.domain import (
    EvidenceChunk,
    ExtractedDocument,
    FetchedDocument,
    FetchRequest,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMRole,
    LLMUsage,
    SearchRequest,
    SearchResult,
    Source,
)
from safe_web_research.extraction import FakeExtractor
from safe_web_research.fetch import FakeFetcher
from safe_web_research.llm import FakeLLMProvider
from safe_web_research.search import FakeSearchProvider


def _search_result() -> SearchResult:
    return SearchResult(
        result_id="result-1",
        url="https://example.com/article",
        title="Example article",
        snippet="Example search snippet.",
        rank=1,
        provider="fake",
    )


def _fetched_document() -> FetchedDocument:
    return FetchedDocument(
        requested_url="https://example.com/article",
        final_url="https://example.com/article",
        status_code=200,
        content_type="text/html",
        body=b"<html><body>Example content.</body></html>",
    )


def _extracted_document() -> ExtractedDocument:
    now = datetime.now(UTC)

    source = Source(
        source_id="source-1",
        url="https://example.com/article",
        title="Example article",
        provider="fake",
        retrieved_at=now,
        content_hash="a" * 64,
    )

    chunk = EvidenceChunk(
        chunk_id="evidence-1",
        source_id="source-1",
        text="Example content.",
        position=0,
    )

    return ExtractedDocument(
        source=source,
        chunks=[chunk],
    )


@pytest.mark.asyncio
async def test_fake_search_provider_returns_configured_results() -> None:
    provider = FakeSearchProvider({"example query": [_search_result()]})

    request = SearchRequest(query="example query")

    results = await provider.search(request)

    assert [result.result_id for result in results] == ["result-1"]
    assert provider.requests == [request]


@pytest.mark.asyncio
async def test_fake_search_provider_honors_max_results() -> None:
    first = _search_result()

    second = first.model_copy(
        update={
            "result_id": "result-2",
            "rank": 2,
        }
    )

    provider = FakeSearchProvider({"example query": [first, second]})

    results = await provider.search(
        SearchRequest(
            query="example query",
            max_results=1,
        )
    )

    assert [result.result_id for result in results] == ["result-1"]


@pytest.mark.asyncio
async def test_fake_fetcher_returns_configured_document() -> None:
    document = _fetched_document()

    fetcher = FakeFetcher({str(document.requested_url): document})

    request = FetchRequest(url="https://example.com/article")

    result = await fetcher.fetch(request)

    assert result.body == document.body
    assert fetcher.requests == [request]


@pytest.mark.asyncio
async def test_fake_fetcher_fails_for_unknown_url() -> None:
    fetcher = FakeFetcher()

    with pytest.raises(
        LookupError,
        match="No fake document configured",
    ):
        await fetcher.fetch(FetchRequest(url="https://example.com/missing"))


@pytest.mark.asyncio
async def test_fake_extractor_returns_configured_evidence() -> None:
    fetched = _fetched_document()
    extracted = _extracted_document()

    extractor = FakeExtractor({str(fetched.final_url): extracted})

    result = await extractor.extract(fetched)

    assert result.source.source_id == "source-1"
    assert [chunk.chunk_id for chunk in result.chunks] == ["evidence-1"]
    assert extractor.documents == [fetched]


@pytest.mark.asyncio
async def test_fake_llm_provider_returns_responses_in_order() -> None:
    first = LLMResponse(
        content='{"queries":["first"]}',
        model="fake-model",
        usage=LLMUsage(output_tokens=5),
    )

    second = LLMResponse(
        content='{"answer":"second"}',
        model="fake-model",
        usage=LLMUsage(output_tokens=4),
    )

    provider = FakeLLMProvider([first, second])

    request = LLMRequest(
        messages=[
            LLMMessage(
                role=LLMRole.USER,
                content="test",
            )
        ],
    )

    assert (await provider.complete(request)).content == first.content
    assert (await provider.complete(request)).content == second.content
    assert provider.requests == [request, request]


@pytest.mark.asyncio
async def test_fake_llm_provider_fails_when_queue_is_empty() -> None:
    provider = FakeLLMProvider()

    request = LLMRequest(
        messages=[
            LLMMessage(
                role=LLMRole.USER,
                content="test",
            )
        ],
    )

    with pytest.raises(
        LookupError,
        match="No fake LLM response configured",
    ):
        await provider.complete(request)

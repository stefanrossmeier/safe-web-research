from datetime import UTC, datetime

import pytest

from safe_web_research.domain import (
    EvidenceChunk,
    ExtractedDocument,
    FetchedDocument,
    FetchRequest,
    ResearchRequest,
    ResearchResult,
    SearchRequest,
    SearchResult,
    Source,
)
from safe_web_research.extraction import FakeExtractor
from safe_web_research.fetch import FakeFetcher
from safe_web_research.search import FakeSearchProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fake_search_fetch_extract_pipeline_preserves_provenance() -> None:
    now = datetime.now(UTC)
    url = "https://example.com/python"

    search_provider = FakeSearchProvider(
        {
            "Python 3.15 changes": [
                SearchResult(
                    result_id="result-1",
                    url=url,
                    title="Python 3.15",
                    snippet="Python 3.15 has a documented change.",
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
        content_type="text/html",
        body=b"<p>Python 3.15 has a documented change.</p>",
    )

    fetcher = FakeFetcher({url: fetched})

    source = Source(
        source_id="source-1",
        url=url,
        title="Python 3.15",
        provider="fake",
        retrieved_at=now,
        content_hash="b" * 64,
    )

    evidence = EvidenceChunk(
        chunk_id="evidence-1",
        source_id="source-1",
        text="Python 3.15 has a documented change.",
        position=0,
    )

    extractor = FakeExtractor(
        {
            url: ExtractedDocument(
                source=source,
                chunks=[evidence],
            )
        }
    )

    research_request = ResearchRequest(question="What changed in Python 3.15?")

    search_results = await search_provider.search(
        SearchRequest(
            query="Python 3.15 changes",
            max_results=5,
        )
    )

    fetched_document = await fetcher.fetch(
        FetchRequest(
            url=search_results[0].url,
        )
    )

    extracted_document = await extractor.extract(fetched_document)

    result = ResearchResult(
        answer="Synthesis is intentionally not implemented yet.",
        sources=[extracted_document.source],
        evidence=extracted_document.chunks,
        incomplete_reasons=["synthesis_not_implemented"],
    )

    assert research_request.question == ("What changed in Python 3.15?")

    assert result.sources[0].source_id == "source-1"

    assert result.evidence[0].source_id == result.sources[0].source_id

    assert result.incomplete_reasons == ["synthesis_not_implemented"]

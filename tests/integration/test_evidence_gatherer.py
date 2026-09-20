import pytest

from safe_web_research.domain import (
    FetchedDocument,
    ResearchRequest,
    SearchResult,
)
from safe_web_research.extraction import WebExtractor
from safe_web_research.fetch import FakeFetcher
from safe_web_research.research import EvidenceGatherer
from safe_web_research.search import FakeSearchProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_evidence_gatherer_collects_real_extracted_evidence() -> None:
    first_url = "https://one.example/article"
    second_url = "https://two.example/article"

    search = FakeSearchProvider(
        {
            "Python security": [
                SearchResult(
                    result_id="one",
                    url=first_url,
                    title="One",
                    snippet="First result",
                    rank=1,
                    provider="fake",
                ),
                SearchResult(
                    result_id="two",
                    url=second_url,
                    title="Two",
                    snippet="Second result",
                    rank=2,
                    provider="fake",
                ),
            ]
        }
    )

    first = FetchedDocument(
        requested_url=first_url,
        final_url=first_url,
        status_code=200,
        content_type="text/html",
        body=b"""
        <html>
          <title>First source</title>
          <main>
            <p>First factual statement.</p>
          </main>
        </html>
        """,
    )

    second = FetchedDocument(
        requested_url=second_url,
        final_url=second_url,
        status_code=200,
        content_type="text/plain",
        body=b"Second factual statement.",
    )

    fetcher = FakeFetcher(
        {
            first_url: first,
            second_url: second,
        }
    )

    gatherer = EvidenceGatherer(
        search,
        fetcher,
        WebExtractor(),
    )

    result = await gatherer.gather(
        ResearchRequest(
            question="Python security",
        )
    )

    assert result.queries == ["Python security"]

    assert len(result.sources) == 2
    assert len(result.evidence) == 2

    assert result.usage.search_requests == 1
    assert result.usage.fetch_attempts == 2
    assert result.usage.pages_fetched == 2

    assert result.usage.bytes_fetched == (len(first.body) + len(second.body))

    assert result.incomplete_reasons == []

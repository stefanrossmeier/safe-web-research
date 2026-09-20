import pytest

from safe_web_research.domain import (
    FetchedDocument,
    FetchRequest,
    ResearchBudget,
    ResearchRequest,
    SearchResult,
)
from safe_web_research.extraction import WebExtractor
from safe_web_research.fetch import FakeFetcher, FetchConnectionError
from safe_web_research.research import (
    EvidenceGatherer,
    StoppingPolicy,
)
from safe_web_research.search import FakeSearchProvider


def _result(
    result_id: str,
    url: str,
    rank: int,
) -> SearchResult:
    return SearchResult(
        result_id=result_id,
        url=url,
        title=result_id,
        snippet=result_id,
        rank=rank,
        provider="fake",
    )


class _FailThenSucceedFetcher:
    def __init__(
        self,
        failing_url: str,
        successful_document: FetchedDocument,
    ) -> None:
        self._failing_url = failing_url
        self._successful_document = successful_document
        self.requests: list[FetchRequest] = []

    async def fetch(self, request: FetchRequest) -> FetchedDocument:
        self.requests.append(request.model_copy(deep=True))

        if str(request.url) == self._failing_url:
            raise FetchConnectionError("simulated fetch failure")

        return self._successful_document.model_copy(deep=True)


def _document(
    url: str,
    body: bytes,
) -> FetchedDocument:
    return FetchedDocument(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/plain",
        body=body,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gatherer_never_exceeds_page_budget() -> None:
    first_url = "https://one.example/"
    second_url = "https://two.example/"

    search = FakeSearchProvider(
        {
            "query": [
                _result(
                    "one",
                    first_url,
                    1,
                ),
                _result(
                    "two",
                    second_url,
                    2,
                ),
            ]
        }
    )

    fetcher = FakeFetcher(
        {
            first_url: _document(
                first_url,
                b"one",
            ),
            second_url: _document(
                second_url,
                b"two",
            ),
        }
    )

    gatherer = EvidenceGatherer(
        search,
        fetcher,
        WebExtractor(),
    )

    result = await gatherer.gather(
        ResearchRequest(
            question="query",
            budget=ResearchBudget(
                max_searches=1,
                max_pages=1,
            ),
        )
    )

    assert len(fetcher.requests) == 1
    assert result.usage.fetch_attempts == 1
    assert result.usage.pages_fetched == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_failed_fetch_attempt_does_not_consume_successful_page_budget() -> None:
    failing_url = "https://failed.example/"
    successful_url = "https://success.example/"

    search = FakeSearchProvider(
        {
            "query": [
                _result("failed", failing_url, 1),
                _result("success", successful_url, 2),
            ]
        }
    )

    fetcher = _FailThenSucceedFetcher(
        failing_url,
        _document(successful_url, b"useful content"),
    )

    result = await EvidenceGatherer(
        search,
        fetcher,
        WebExtractor(),
    ).gather(
        ResearchRequest(
            question="query",
            budget=ResearchBudget(
                max_searches=1,
                max_fetch_attempts=2,
                max_pages=1,
            ),
        )
    )

    assert len(fetcher.requests) == 2
    assert result.usage.fetch_attempts == 2
    assert result.usage.pages_fetched == 1
    assert len(result.sources) == 1
    assert "max_pages_reached" not in result.incomplete_reasons


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gatherer_never_exceeds_search_budget() -> None:
    search = FakeSearchProvider(
        {
            "first": [],
            "second": [],
        }
    )

    gatherer = EvidenceGatherer(
        search,
        FakeFetcher(),
        WebExtractor(),
        stopping_policy=StoppingPolicy(max_consecutive_empty_queries=10),
    )

    result = await gatherer.gather(
        ResearchRequest(
            question="unused",
            budget=ResearchBudget(
                max_searches=1,
                max_pages=10,
            ),
        ),
        queries=[
            "first",
            "second",
        ],
    )

    assert [request.query for request in search.requests] == ["first"]

    assert "max_searches_reached" in result.incomplete_reasons


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gatherer_reduces_fetch_limit_as_total_budget_is_consumed() -> None:
    first_url = "https://one.example/"
    second_url = "https://two.example/"

    search = FakeSearchProvider(
        {
            "query": [
                _result(
                    "one",
                    first_url,
                    1,
                ),
                _result(
                    "two",
                    second_url,
                    2,
                ),
            ]
        }
    )

    fetcher = FakeFetcher(
        {
            first_url: _document(
                first_url,
                b"12345678",
            ),
            second_url: _document(
                second_url,
                b"90",
            ),
        }
    )

    gatherer = EvidenceGatherer(
        search,
        fetcher,
        WebExtractor(),
    )

    result = await gatherer.gather(
        ResearchRequest(
            question="query",
            budget=ResearchBudget(
                max_searches=1,
                max_pages=2,
                max_bytes_per_page=10,
                max_total_bytes=10,
            ),
        )
    )

    assert [request.max_bytes for request in fetcher.requests] == [
        10,
        2,
    ]

    assert result.usage.bytes_fetched == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gatherer_fetches_duplicate_url_only_once() -> None:
    url = "https://one.example/"

    search = FakeSearchProvider(
        {
            "first": [
                _result(
                    "one",
                    url,
                    1,
                )
            ],
            "second": [
                _result(
                    "duplicate",
                    url,
                    1,
                )
            ],
        }
    )

    fetcher = FakeFetcher(
        {
            url: _document(
                url,
                b"useful content",
            ),
        }
    )

    gatherer = EvidenceGatherer(
        search,
        fetcher,
        WebExtractor(),
        stopping_policy=StoppingPolicy(max_consecutive_empty_queries=10),
    )

    result = await gatherer.gather(
        ResearchRequest(
            question="unused",
        ),
        queries=[
            "first",
            "second",
        ],
    )

    assert len(fetcher.requests) == 1
    assert len(result.sources) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gatherer_stops_after_repeated_queries_add_no_evidence() -> None:
    search = FakeSearchProvider(
        {
            "one": [],
            "two": [],
            "three": [],
        }
    )

    gatherer = EvidenceGatherer(
        search,
        FakeFetcher(),
        WebExtractor(),
        stopping_policy=StoppingPolicy(max_consecutive_empty_queries=2),
    )

    result = await gatherer.gather(
        ResearchRequest(
            question="unused",
        ),
        queries=[
            "one",
            "two",
            "three",
        ],
    )

    assert [request.query for request in search.requests] == [
        "one",
        "two",
    ]

    assert "no_new_evidence" in result.incomplete_reasons

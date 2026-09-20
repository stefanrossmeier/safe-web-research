from datetime import date

import httpx
import pytest
import respx

from safe_web_research.domain import SearchRequest
from safe_web_research.search import (
    BraveSearchProvider,
    SearchProviderAuthenticationError,
    SearchProviderRateLimitError,
    SearchProviderRequestError,
    SearchProviderResponseError,
    SearchProviderUnavailableError,
)
from safe_web_research.search.brave import BRAVE_WEB_SEARCH_URL


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_normalizes_web_results() -> None:
    route = respx.get(BRAVE_WEB_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "search",
                "web": {
                    "type": "search",
                    "results": [
                        {
                            "title": "Python",
                            "url": "https://www.python.org/",
                            "description": "Official Python site.",
                            "language": "en",
                            "some_future_field": "ignored",
                        }
                    ],
                },
                "some_future_section": {"value": "ignored"},
            },
        )
    )

    provider = BraveSearchProvider("test-api-key")

    results = await provider.search(
        SearchRequest(
            query="Python",
            max_results=5,
            country="DE",
            language="de",
        )
    )

    assert route.called

    request = route.calls[0].request

    assert request.headers["X-Subscription-Token"] == ("test-api-key")
    assert request.url.params["q"] == "Python"
    assert request.url.params["count"] == "5"
    assert request.url.params["country"] == "DE"
    assert request.url.params["search_lang"] == "de"
    assert request.url.params["spellcheck"] == "false"
    assert request.url.params["text_decorations"] == "false"

    assert len(results) == 1
    assert results[0].provider == "brave"
    assert results[0].rank == 1
    assert str(results[0].url) == "https://www.python.org/"
    assert results[0].title == "Python"
    assert results[0].snippet == "Official Python site."
    assert results[0].published_at is None


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_returns_empty_list_without_web_results() -> None:
    respx.get(BRAVE_WEB_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "type": "search",
                "query": {"original": "nothing"},
            },
        )
    )

    provider = BraveSearchProvider("test-api-key")

    results = await provider.search(SearchRequest(query="nothing"))

    assert results == []


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_builds_domain_filters() -> None:
    route = respx.get(BRAVE_WEB_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={"web": {"results": []}},
        )
    )

    provider = BraveSearchProvider("test-api-key")

    await provider.search(
        SearchRequest(
            query="python security",
            include_domains=[
                "python.org",
                "docs.python.org",
            ],
            exclude_domains=["example.com"],
        )
    )

    query = route.calls[0].request.url.params["q"]

    assert query == (
        "python security (site:python.org OR site:docs.python.org) NOT site:example.com"
    )


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_uses_freshness_preset() -> None:
    route = respx.get(BRAVE_WEB_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={"web": {"results": []}},
        )
    )

    provider = BraveSearchProvider("test-api-key")

    await provider.search(
        SearchRequest(
            query="news",
            freshness_days=7,
        )
    )

    assert route.calls[0].request.url.params["freshness"] == "pw"


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_builds_exact_freshness_range() -> None:
    route = respx.get(BRAVE_WEB_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={"web": {"results": []}},
        )
    )

    provider = BraveSearchProvider(
        "test-api-key",
        today_provider=lambda: date(2026, 9, 20),
    )

    await provider.search(
        SearchRequest(
            query="news",
            freshness_days=30,
        )
    )

    assert route.calls[0].request.url.params["freshness"] == "2026-08-22to2026-09-20"


@pytest.mark.asyncio
async def test_brave_search_rejects_provider_query_over_600_chars() -> None:
    provider = BraveSearchProvider("test-api-key")

    request = SearchRequest(query="a" * 600)

    request = request.model_copy(update={"include_domains": ["example.com"]})

    with pytest.raises(
        SearchProviderRequestError,
        match="600 character",
    ):
        await provider.search(request)


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_maps_authentication_error() -> None:
    respx.get(BRAVE_WEB_SEARCH_URL).mock(return_value=httpx.Response(401))

    provider = BraveSearchProvider("test-api-key")

    with pytest.raises(SearchProviderAuthenticationError):
        await provider.search(SearchRequest(query="test"))


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_maps_rate_limit_and_reset_header() -> None:
    respx.get(BRAVE_WEB_SEARCH_URL).mock(
        return_value=httpx.Response(
            429,
            headers={
                "X-RateLimit-Reset": "2, 1000",
            },
        )
    )

    provider = BraveSearchProvider("test-api-key")

    with pytest.raises(SearchProviderRateLimitError) as exc_info:
        await provider.search(SearchRequest(query="test"))

    assert exc_info.value.reset_seconds == "2, 1000"


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_maps_server_error() -> None:
    respx.get(BRAVE_WEB_SEARCH_URL).mock(return_value=httpx.Response(503))

    provider = BraveSearchProvider("test-api-key")

    with pytest.raises(SearchProviderUnavailableError):
        await provider.search(SearchRequest(query="test"))


@respx.mock
@pytest.mark.asyncio
async def test_brave_search_rejects_malformed_result() -> None:
    respx.get(BRAVE_WEB_SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Bad URL",
                            "url": "file:///etc/passwd",
                            "description": "Must not normalize.",
                        }
                    ]
                }
            },
        )
    )

    provider = BraveSearchProvider("test-api-key")

    with pytest.raises(SearchProviderResponseError):
        await provider.search(SearchRequest(query="test"))

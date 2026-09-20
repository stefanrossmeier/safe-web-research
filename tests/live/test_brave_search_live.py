import os

import pytest

from safe_web_research.domain import SearchRequest
from safe_web_research.search import BraveSearchProvider


@pytest.mark.live
@pytest.mark.asyncio
async def test_brave_search_live() -> None:
    api_key = os.getenv("BRAVE_API_KEY")

    if not api_key:
        pytest.skip("BRAVE_API_KEY is not configured")

    provider = BraveSearchProvider(api_key)

    results = await provider.search(
        SearchRequest(
            query="Python programming language",
            max_results=3,
        )
    )

    assert results
    assert len(results) <= 3

    for result in results:
        assert result.provider == "brave"
        assert result.rank >= 1
        assert str(result.url).startswith(("http://", "https://"))

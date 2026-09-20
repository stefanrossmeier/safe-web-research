import pytest

from safe_web_research.domain import FetchRequest
from safe_web_research.fetch import (
    SafeFetcher,
    SystemDNSResolver,
    URLPolicy,
)


@pytest.mark.live
@pytest.mark.asyncio
async def test_safe_fetcher_live_https() -> None:
    fetcher = SafeFetcher(URLPolicy(SystemDNSResolver()))

    document = await fetcher.fetch(
        FetchRequest(
            url="https://example.com/",
            max_bytes=200_000,
            max_redirects=2,
        )
    )

    assert document.status_code == 200
    assert document.content_type == "text/html"
    assert document.body
    assert str(document.final_url).startswith("https://example.com/")

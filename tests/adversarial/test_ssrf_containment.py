import httpx
import pytest

from safe_web_research.domain import FetchRequest
from safe_web_research.fetch import (
    FakeDNSResolver,
    FetchPolicyError,
    SafeFetcher,
    URLPolicy,
)


@pytest.mark.adversarial
@pytest.mark.asyncio
async def test_redirect_to_cloud_metadata_is_blocked_before_second_request() -> None:
    seen: list[httpx.Request] = []

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        seen.append(request)

        return httpx.Response(
            302,
            headers={"Location": "https://metadata.attacker.example/latest/meta-data/"},
        )

    resolver = FakeDNSResolver(
        {
            "public.example": ["1.1.1.1"],
            "metadata.attacker.example": ["169.254.169.254"],
        }
    )

    fetcher = SafeFetcher(
        URLPolicy(resolver),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchPolicyError,
        match="non-global address",
    ):
        await fetcher.fetch(FetchRequest(url="https://public.example/"))

    assert len(seen) == 1

    assert resolver.requests == [
        "public.example",
        "metadata.attacker.example",
    ]

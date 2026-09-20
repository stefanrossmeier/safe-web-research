import pytest

from safe_web_research.fetch import (
    FakeDNSResolver,
    FetchResolutionError,
)


@pytest.mark.asyncio
async def test_fake_dns_resolver_returns_configured_addresses() -> None:
    resolver = FakeDNSResolver(
        {
            "example.com": [
                "1.1.1.1",
                "2606:4700:4700::1111",
            ]
        }
    )

    addresses = await resolver.resolve("EXAMPLE.COM")

    assert [str(address) for address in addresses] == [
        "1.1.1.1",
        "2606:4700:4700::1111",
    ]

    assert resolver.requests == ["example.com"]


@pytest.mark.asyncio
async def test_fake_dns_resolver_normalizes_trailing_dot() -> None:
    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    addresses = await resolver.resolve("example.com.")

    assert [str(address) for address in addresses] == ["1.1.1.1"]

    assert resolver.requests == ["example.com"]


@pytest.mark.asyncio
async def test_fake_dns_resolver_fails_for_unknown_hostname() -> None:
    resolver = FakeDNSResolver()

    with pytest.raises(
        FetchResolutionError,
        match="No fake DNS result configured",
    ):
        await resolver.resolve("missing.example")

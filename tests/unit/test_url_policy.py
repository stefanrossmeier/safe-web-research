import pytest
from pydantic import HttpUrl

from safe_web_research.fetch import (
    FakeDNSResolver,
    FetchPolicyError,
    FetchResolutionError,
    URLPolicy,
)


@pytest.mark.asyncio
async def test_policy_allows_public_https_target() -> None:
    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    policy = URLPolicy(resolver)

    target = await policy.validate(HttpUrl("https://example.com/article"))

    assert target.hostname == "example.com"
    assert target.port == 443
    assert [str(address) for address in target.addresses] == ["1.1.1.1"]
    assert resolver.requests == ["example.com"]


@pytest.mark.asyncio
async def test_policy_allows_public_http_target() -> None:
    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    policy = URLPolicy(resolver)

    target = await policy.validate(HttpUrl("http://example.com/article"))

    assert target.port == 80


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.1.1/",
        "http://169.254.169.254/",
        "http://100.64.0.1/",
        "http://[::1]/",
        "http://[fe80::1]/",
    ],
)
@pytest.mark.asyncio
async def test_policy_blocks_non_global_ip_literals(
    url: str,
) -> None:
    resolver = FakeDNSResolver()
    policy = URLPolicy(resolver)

    with pytest.raises(
        FetchPolicyError,
        match="non-global address",
    ):
        await policy.validate(HttpUrl(url))

    assert resolver.requests == []


@pytest.mark.asyncio
async def test_policy_blocks_hostname_resolving_to_private_ip() -> None:
    resolver = FakeDNSResolver(
        {
            "attacker.example": ["127.0.0.1"],
        }
    )

    policy = URLPolicy(resolver)

    with pytest.raises(
        FetchPolicyError,
        match="non-global address",
    ):
        await policy.validate(HttpUrl("https://attacker.example/"))


@pytest.mark.asyncio
async def test_policy_rejects_mixed_public_and_private_dns_answers() -> None:
    resolver = FakeDNSResolver(
        {
            "attacker.example": [
                "1.1.1.1",
                "127.0.0.1",
            ],
        }
    )

    policy = URLPolicy(resolver)

    with pytest.raises(
        FetchPolicyError,
        match="non-global address",
    ):
        await policy.validate(HttpUrl("https://attacker.example/"))


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://something.localhost/",
        "http://printer.local/",
        "http://printer/",
    ],
)
@pytest.mark.asyncio
async def test_policy_blocks_internal_style_hostnames_before_dns(
    url: str,
) -> None:
    resolver = FakeDNSResolver()
    policy = URLPolicy(resolver)

    with pytest.raises(FetchPolicyError):
        await policy.validate(HttpUrl(url))

    assert resolver.requests == []


@pytest.mark.asyncio
async def test_policy_rejects_url_userinfo() -> None:
    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    policy = URLPolicy(resolver)

    with pytest.raises(
        FetchPolicyError,
        match="user information",
    ):
        await policy.validate(HttpUrl("https://user:password@example.com/"))

    assert resolver.requests == []


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com:8443/",
        "http://example.com:8080/",
    ],
)
@pytest.mark.asyncio
async def test_policy_rejects_nonstandard_web_ports(
    url: str,
) -> None:
    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    policy = URLPolicy(resolver)

    with pytest.raises(
        FetchPolicyError,
        match="Non-standard",
    ):
        await policy.validate(HttpUrl(url))

    assert resolver.requests == []


@pytest.mark.asyncio
async def test_policy_propagates_resolution_failure() -> None:
    resolver = FakeDNSResolver()
    policy = URLPolicy(resolver)

    with pytest.raises(FetchResolutionError):
        await policy.validate(HttpUrl("https://missing.example/"))

import gzip

import httpx
import pytest

from safe_web_research.domain import FetchRequest
from safe_web_research.fetch import (
    FakeDNSResolver,
    FetchConnectionError,
    FetchContentEncodingError,
    FetchContentTypeError,
    FetchPolicyError,
    FetchRedirectError,
    FetchSizeLimitError,
    FetchTimeoutError,
    SafeFetcher,
    URLPolicy,
)


class _BytesStream(httpx.AsyncByteStream):
    def __init__(
        self,
        *chunks: bytes,
    ) -> None:
        self._chunks = chunks

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk


def _response(
    status_code: int,
    *,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> httpx.Response:
    return httpx.Response(
        status_code,
        headers=headers,
        stream=_BytesStream(body),
    )


def _fetcher(
    resolver: FakeDNSResolver,
    transport: httpx.AsyncBaseTransport,
) -> SafeFetcher:
    return SafeFetcher(
        URLPolicy(resolver),
        transport=transport,
    )


@pytest.mark.asyncio
async def test_fetcher_connects_to_validated_ip_and_preserves_host_and_sni() -> None:
    seen: list[httpx.Request] = []

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        seen.append(request)

        return _response(
            200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
            },
            body=b"<html>ok</html>",
        )

    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    document = await fetcher.fetch(FetchRequest(url="https://example.com/path?q=1"))

    assert len(seen) == 1

    outbound = seen[0]

    assert str(outbound.url) == "https://1.1.1.1/path?q=1"

    assert outbound.headers["Host"] == "example.com"

    assert outbound.headers["Accept-Encoding"] == "gzip, identity"

    assert outbound.headers["Connection"] == "close"

    assert outbound.extensions["sni_hostname"] == "example.com"

    assert str(document.requested_url) == "https://example.com/path?q=1"

    assert str(document.final_url) == "https://example.com/path?q=1"

    assert document.content_type == "text/html"
    assert document.body == b"<html>ok</html>"
    assert document.redirect_chain == []


@pytest.mark.asyncio
async def test_fetcher_does_not_set_sni_for_plain_http() -> None:
    seen: list[httpx.Request] = []

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        seen.append(request)

        return _response(
            200,
            headers={
                "Content-Type": "text/plain",
            },
            body=b"ok",
        )

    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    await fetcher.fetch(FetchRequest(url="http://example.com/"))

    assert "sni_hostname" not in seen[0].extensions


@pytest.mark.asyncio
async def test_fetcher_revalidates_each_redirect_before_second_request() -> None:
    seen: list[httpx.Request] = []

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        seen.append(request)

        if request.headers["Host"] == "start.example":
            return _response(
                302,
                headers={
                    "Location": "https://final.example/page",
                },
            )

        return _response(
            200,
            headers={
                "Content-Type": "text/html",
            },
            body=b"final",
        )

    resolver = FakeDNSResolver(
        {
            "start.example": ["1.1.1.1"],
            "final.example": ["8.8.8.8"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    document = await fetcher.fetch(FetchRequest(url="https://start.example/"))

    assert resolver.requests == [
        "start.example",
        "final.example",
    ]

    assert [request.url.host for request in seen] == [
        "1.1.1.1",
        "8.8.8.8",
    ]

    assert [request.headers["Host"] for request in seen] == [
        "start.example",
        "final.example",
    ]

    assert [str(url) for url in document.redirect_chain] == ["https://final.example/page"]

    assert str(document.final_url) == "https://final.example/page"


@pytest.mark.asyncio
async def test_fetcher_blocks_redirect_to_private_address_before_connecting() -> None:
    seen: list[httpx.Request] = []

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        seen.append(request)

        return _response(
            302,
            headers={
                "Location": "https://evil.example/private",
            },
        )

    resolver = FakeDNSResolver(
        {
            "start.example": ["1.1.1.1"],
            "evil.example": ["127.0.0.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchPolicyError,
        match="non-global address",
    ):
        await fetcher.fetch(FetchRequest(url="https://start.example/"))

    assert len(seen) == 1

    assert resolver.requests == [
        "start.example",
        "evil.example",
    ]


@pytest.mark.asyncio
async def test_fetcher_detects_redirect_loop() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            302,
            headers={
                "Location": "https://loop.example/",
            },
        )

    resolver = FakeDNSResolver(
        {
            "loop.example": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchRedirectError,
        match="loop",
    ):
        await fetcher.fetch(FetchRequest(url="https://loop.example/"))


@pytest.mark.asyncio
async def test_fetcher_enforces_zero_redirect_budget() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            302,
            headers={
                "Location": "https://other.example/",
            },
        )

    resolver = FakeDNSResolver(
        {
            "start.example": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchRedirectError,
        match="Redirect limit exceeded: 0",
    ):
        await fetcher.fetch(
            FetchRequest(
                url="https://start.example/",
                max_redirects=0,
            )
        )


@pytest.mark.asyncio
async def test_fetcher_rejects_redirect_without_location() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(302)

    resolver = FakeDNSResolver(
        {
            "start.example": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchRedirectError,
        match="missing Location",
    ):
        await fetcher.fetch(FetchRequest(url="https://start.example/"))


@pytest.mark.asyncio
async def test_fetcher_rejects_disallowed_content_type() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            headers={
                "Content-Type": "application/pdf",
            },
            body=b"%PDF",
        )

    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchContentTypeError,
        match="application/pdf",
    ):
        await fetcher.fetch(FetchRequest(url="https://example.com/file.pdf"))


@pytest.mark.asyncio
async def test_fetcher_rejects_missing_content_type() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            body=b"unknown",
        )

    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchContentTypeError,
        match="missing Content-Type",
    ):
        await fetcher.fetch(FetchRequest(url="https://example.com/"))


@pytest.mark.asyncio
async def test_fetcher_safely_decompresses_gzip_with_decompressed_limit() -> None:
    body = b"Python documentation " * 20
    compressed = gzip.compress(body)

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            headers={
                "Content-Type": "text/html",
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            },
            body=compressed,
        )

    resolver = FakeDNSResolver({"example.com": ["1.1.1.1"]})
    fetcher = _fetcher(resolver, httpx.MockTransport(handler))

    document = await fetcher.fetch(
        FetchRequest(
            url="https://example.com/",
            max_bytes=len(body),
        )
    )

    assert document.body == body


@pytest.mark.asyncio
async def test_fetcher_rejects_gzip_decompression_bomb_over_limit() -> None:
    compressed = gzip.compress(b"A" * 10_000)

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            headers={
                "Content-Type": "text/plain",
                "Content-Encoding": "gzip",
            },
            body=compressed,
        )

    resolver = FakeDNSResolver({"example.com": ["1.1.1.1"]})
    fetcher = _fetcher(resolver, httpx.MockTransport(handler))

    with pytest.raises(
        FetchSizeLimitError,
        match="Decompressed response body exceeds",
    ):
        await fetcher.fetch(
            FetchRequest(
                url="https://example.com/",
                max_bytes=1_000,
            )
        )


@pytest.mark.asyncio
async def test_fetcher_rejects_unsupported_content_encoding() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            headers={
                "Content-Type": "text/html",
                "Content-Encoding": "br",
            },
            body=b"compressed",
        )

    resolver = FakeDNSResolver({"example.com": ["1.1.1.1"]})
    fetcher = _fetcher(resolver, httpx.MockTransport(handler))

    with pytest.raises(
        FetchContentEncodingError,
        match="br",
    ):
        await fetcher.fetch(FetchRequest(url="https://example.com/"))


@pytest.mark.asyncio
async def test_fetcher_rejects_declared_body_larger_than_limit() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            headers={
                "Content-Type": "text/plain",
                "Content-Length": "100",
            },
            body=b"small",
        )

    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchSizeLimitError,
        match="Declared response size",
    ):
        await fetcher.fetch(
            FetchRequest(
                url="https://example.com/",
                max_bytes=10,
            )
        )


@pytest.mark.asyncio
async def test_fetcher_stops_stream_when_body_exceeds_limit() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            headers={
                "Content-Type": "text/plain",
            },
            body=b"123456",
        )

    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchSizeLimitError,
        match="exceeds limit",
    ):
        await fetcher.fetch(
            FetchRequest(
                url="https://example.com/",
                max_bytes=5,
            )
        )


@pytest.mark.asyncio
async def test_fetcher_tries_next_validated_address_after_connect_error() -> None:
    seen_hosts: list[str] = []

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        seen_hosts.append(request.url.host)

        if request.url.host == "1.1.1.1":
            raise httpx.ConnectError(
                "first address failed",
                request=request,
            )

        return _response(
            200,
            headers={
                "Content-Type": "text/plain",
            },
            body=b"ok",
        )

    resolver = FakeDNSResolver(
        {
            "example.com": [
                "1.1.1.1",
                "8.8.8.8",
            ],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    document = await fetcher.fetch(FetchRequest(url="https://example.com/"))

    assert seen_hosts == [
        "1.1.1.1",
        "8.8.8.8",
    ]

    assert document.body == b"ok"


@pytest.mark.asyncio
async def test_fetcher_maps_timeout_after_all_addresses_fail() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ReadTimeout(
            "timed out",
            request=request,
        )

    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchTimeoutError,
        match="Timed out",
    ):
        await fetcher.fetch(FetchRequest(url="https://example.com/"))


@pytest.mark.asyncio
async def test_fetcher_maps_connection_failure() -> None:
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "failed",
            request=request,
        )

    resolver = FakeDNSResolver(
        {
            "example.com": ["1.1.1.1"],
        }
    )

    fetcher = _fetcher(
        resolver,
        httpx.MockTransport(handler),
    )

    with pytest.raises(
        FetchConnectionError,
        match="Failed connecting",
    ):
        await fetcher.fetch(FetchRequest(url="https://example.com/"))


@pytest.mark.asyncio
async def test_fetcher_rejects_truncated_gzip_body() -> None:
    compressed = gzip.compress(b"bounded content")[:-4]

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            headers={
                "Content-Type": "text/plain",
                "Content-Encoding": "gzip",
            },
            body=compressed,
        )

    resolver = FakeDNSResolver({"example.com": ["1.1.1.1"]})
    fetcher = _fetcher(resolver, httpx.MockTransport(handler))

    with pytest.raises(
        FetchContentEncodingError,
        match="Truncated gzip",
    ):
        await fetcher.fetch(FetchRequest(url="https://example.com/"))


@pytest.mark.asyncio
async def test_fetcher_rejects_concatenated_gzip_members() -> None:
    compressed = gzip.compress(b"first") + gzip.compress(b"second")

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return _response(
            200,
            headers={
                "Content-Type": "text/plain",
                "Content-Encoding": "gzip",
            },
            body=compressed,
        )

    resolver = FakeDNSResolver({"example.com": ["1.1.1.1"]})
    fetcher = _fetcher(resolver, httpx.MockTransport(handler))

    with pytest.raises(
        FetchContentEncodingError,
        match="Concatenated gzip",
    ):
        await fetcher.fetch(FetchRequest(url="https://example.com/"))

import zlib
from collections.abc import Iterable
from ipaddress import IPv6Address, ip_address

import httpx
from pydantic import HttpUrl, ValidationError

from safe_web_research.domain.fetch import FetchedDocument, FetchRequest
from safe_web_research.fetch.base import Fetcher
from safe_web_research.fetch.errors import (
    FetchConfigurationError,
    FetchConnectionError,
    FetchContentEncodingError,
    FetchContentTypeError,
    FetchRedirectError,
    FetchSizeLimitError,
    FetchTimeoutError,
)
from safe_web_research.fetch.resolver import IPAddress
from safe_web_research.fetch.url_policy import URLPolicy, ValidatedTarget

_REDIRECT_STATUS_CODES = frozenset(
    {
        301,
        302,
        303,
        307,
        308,
    }
)

_DEFAULT_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "text/plain",
        "application/xhtml+xml",
    }
)


class SafeFetcher(Fetcher):
    """Bounded HTTP(S) fetcher that preserves the validated network target."""

    def __init__(
        self,
        url_policy: URLPolicy,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 10.0,
        allowed_content_types: Iterable[str] = _DEFAULT_ALLOWED_CONTENT_TYPES,
        user_agent: str = "safe-web-research/0.1",
    ) -> None:
        if connect_timeout_seconds <= 0:
            raise FetchConfigurationError("connect timeout must be greater than zero")

        if read_timeout_seconds <= 0:
            raise FetchConfigurationError("read timeout must be greater than zero")

        normalized_content_types = frozenset(
            content_type.strip().lower()
            for content_type in allowed_content_types
            if content_type.strip()
        )

        if not normalized_content_types:
            raise FetchConfigurationError("at least one allowed content type is required")

        if not user_agent.strip():
            raise FetchConfigurationError("user agent must not be empty")

        self._url_policy = url_policy
        self._transport = transport
        self._connect_timeout_seconds = connect_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._allowed_content_types = normalized_content_types
        self._user_agent = user_agent.strip()

    async def fetch(
        self,
        request: FetchRequest,
    ) -> FetchedDocument:
        current_url = request.url

        redirect_chain: list[HttpUrl] = []
        visited = {str(current_url)}

        timeout = httpx.Timeout(
            connect=self._connect_timeout_seconds,
            read=self._read_timeout_seconds,
            write=self._read_timeout_seconds,
            pool=self._connect_timeout_seconds,
        )

        async with httpx.AsyncClient(
            transport=self._transport,
            timeout=timeout,
            follow_redirects=False,
            http2=False,
            limits=httpx.Limits(
                max_connections=1,
                max_keepalive_connections=0,
            ),
            trust_env=False,
        ) as client:
            while True:
                target = await self._url_policy.validate(current_url)

                response = await self._send_to_validated_target(
                    client,
                    target,
                )

                try:
                    if response.status_code in _REDIRECT_STATUS_CODES:
                        current_url = self._redirect_target(
                            current_url,
                            response,
                            redirect_chain=redirect_chain,
                            visited=visited,
                            max_redirects=request.max_redirects,
                        )
                        continue

                    content_type = self._validate_content_type(response)

                    content_encoding = self._validate_content_encoding(response)

                    self._validate_declared_size(
                        response,
                        request.max_bytes,
                    )

                    body = await self._read_bounded_body(
                        response,
                        request.max_bytes,
                        content_encoding=content_encoding,
                    )

                    return FetchedDocument(
                        requested_url=request.url,
                        final_url=current_url,
                        status_code=response.status_code,
                        content_type=content_type,
                        body=body,
                        redirect_chain=redirect_chain,
                    )

                finally:
                    await response.aclose()

    async def _send_to_validated_target(
        self,
        client: httpx.AsyncClient,
        target: ValidatedTarget,
    ) -> httpx.Response:
        last_error: FetchConnectionError | FetchTimeoutError | None = None

        last_cause: Exception | None = None

        for address in target.addresses:
            request = self._build_pinned_request(
                target,
                address,
            )

            try:
                return await client.send(
                    request,
                    stream=True,
                )

            except httpx.TimeoutException as exc:
                last_error = FetchTimeoutError(
                    f"Timed out connecting to validated address: {address}"
                )
                last_cause = exc

            except httpx.RequestError as exc:
                last_error = FetchConnectionError(
                    f"Failed connecting to validated address: {address}"
                )
                last_cause = exc

        if last_error is None:
            raise FetchConnectionError("Validated target contains no addresses")

        raise last_error from last_cause

    def _build_pinned_request(
        self,
        target: ValidatedTarget,
        address: IPAddress,
    ) -> httpx.Request:
        logical_url = httpx.URL(str(target.url))

        connection_url = logical_url.copy_with(host=str(address))

        headers = {
            "Accept": ("text/html, application/xhtml+xml, text/plain;q=0.9"),
            "Accept-Encoding": "gzip, identity",
            "Connection": "close",
            "Host": self._host_header(target.hostname),
            "User-Agent": self._user_agent,
        }

        extensions = (
            {
                "sni_hostname": target.hostname,
            }
            if target.url.scheme.lower() == "https"
            else {}
        )

        return httpx.Request(
            "GET",
            connection_url,
            headers=headers,
            extensions=extensions,
        )

    @staticmethod
    def _host_header(
        hostname: str,
    ) -> str:
        try:
            address = ip_address(hostname)
        except ValueError:
            return hostname

        if isinstance(
            address,
            IPv6Address,
        ):
            return f"[{hostname}]"

        return hostname

    @staticmethod
    def _redirect_target(
        current_url: HttpUrl,
        response: httpx.Response,
        *,
        redirect_chain: list[HttpUrl],
        visited: set[str],
        max_redirects: int,
    ) -> HttpUrl:
        location = response.headers.get("Location")

        if not location:
            raise FetchRedirectError(
                f"HTTP {response.status_code} response is missing Location header"
            )

        if len(redirect_chain) >= max_redirects:
            raise FetchRedirectError(f"Redirect limit exceeded: {max_redirects}")

        try:
            joined = httpx.URL(str(current_url)).join(location)

            redirect_url = HttpUrl(str(joined))

        except (
            httpx.InvalidURL,
            ValidationError,
            ValueError,
        ) as exc:
            raise FetchRedirectError(f"Invalid redirect target: {location!r}") from exc

        normalized = str(redirect_url)

        if normalized in visited:
            raise FetchRedirectError(f"Redirect loop detected at: {normalized}")

        visited.add(normalized)

        redirect_chain.append(redirect_url)

        return redirect_url

    def _validate_content_type(
        self,
        response: httpx.Response,
    ) -> str:
        if "Content-Type" not in response.headers:
            raise FetchContentTypeError("Response is missing Content-Type header")

        raw_content_type: str = response.headers["Content-Type"]

        content_type = raw_content_type.split(";", 1)[0].strip().lower()

        if content_type not in self._allowed_content_types:
            raise FetchContentTypeError(f"Content type is not allowed: {content_type}")

        return content_type

    @staticmethod
    def _validate_content_encoding(
        response: httpx.Response,
    ) -> str:
        encoding = response.headers.get("Content-Encoding")

        if encoding is None:
            return "identity"

        normalized = encoding.strip().lower()

        if normalized in {
            "",
            "identity",
        }:
            return "identity"

        if normalized == "gzip":
            return "gzip"

        raise FetchContentEncodingError(f"Content encoding is not allowed: {normalized}")

    @staticmethod
    def _validate_declared_size(
        response: httpx.Response,
        max_bytes: int,
    ) -> None:
        value = response.headers.get("Content-Length")

        if value is None:
            return

        try:
            content_length = int(value)
        except ValueError:
            return

        if content_length > max_bytes:
            raise FetchSizeLimitError(
                f"Declared response size {content_length} exceeds limit {max_bytes}"
            )

    @classmethod
    async def _read_bounded_body(
        cls,
        response: httpx.Response,
        max_bytes: int,
        *,
        content_encoding: str,
    ) -> bytes:
        if content_encoding == "identity":
            return await cls._read_identity_body(response, max_bytes)

        if content_encoding == "gzip":
            return await cls._read_gzip_body(response, max_bytes)

        raise FetchContentEncodingError(f"Content encoding is not allowed: {content_encoding}")

    @staticmethod
    async def _read_identity_body(
        response: httpx.Response,
        max_bytes: int,
    ) -> bytes:
        body = bytearray()

        async for chunk in response.aiter_raw():
            if len(body) + len(chunk) > max_bytes:
                raise FetchSizeLimitError(f"Response body exceeds limit of {max_bytes} bytes")

            body.extend(chunk)

        return bytes(body)

    @staticmethod
    async def _read_gzip_body(
        response: httpx.Response,
        max_bytes: int,
    ) -> bytes:
        body = bytearray()
        compressed_bytes = 0
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

        try:
            async for chunk in response.aiter_raw():
                compressed_bytes += len(chunk)
                if compressed_bytes > max_bytes:
                    raise FetchSizeLimitError(
                        f"Compressed response body exceeds limit of {max_bytes} bytes"
                    )

                pending = chunk
                while pending:
                    remaining = max_bytes - len(body)
                    decoded = decompressor.decompress(pending, remaining + 1)

                    if len(decoded) > remaining:
                        raise FetchSizeLimitError(
                            f"Decompressed response body exceeds limit of {max_bytes} bytes"
                        )

                    body.extend(decoded)
                    pending = decompressor.unconsumed_tail

                    if not pending:
                        break

            remaining = max_bytes - len(body)
            tail = decompressor.flush(remaining + 1)

        except zlib.error as exc:
            raise FetchContentEncodingError("Invalid gzip response body") from exc

        if len(tail) > remaining:
            raise FetchSizeLimitError(
                f"Decompressed response body exceeds limit of {max_bytes} bytes"
            )

        body.extend(tail)

        if not decompressor.eof:
            raise FetchContentEncodingError("Truncated gzip response body")

        if decompressor.unused_data:
            raise FetchContentEncodingError("Concatenated gzip members are not allowed")

        return bytes(body)

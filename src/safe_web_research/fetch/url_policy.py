from dataclasses import dataclass
from ipaddress import ip_address

from pydantic import HttpUrl

from safe_web_research.domain.domains import validate_domain
from safe_web_research.fetch.errors import FetchPolicyError
from safe_web_research.fetch.resolver import (
    DNSResolver,
    IPAddress,
)

_ALLOWED_PORTS = {
    "http": 80,
    "https": 443,
}

_BLOCKED_HOSTNAMES = {
    "localhost",
}

_BLOCKED_HOSTNAME_SUFFIXES = (
    ".localhost",
    ".local",
)


@dataclass(frozen=True, slots=True)
class ValidatedTarget:
    """Network target approved by deterministic fetch policy."""

    url: HttpUrl
    hostname: str
    port: int
    addresses: tuple[IPAddress, ...]


class URLPolicy:
    """Validate a URL and all addresses it resolves to."""

    def __init__(self, resolver: DNSResolver) -> None:
        self._resolver = resolver

    async def validate(self, url: HttpUrl) -> ValidatedTarget:
        scheme = url.scheme.lower()

        if scheme not in _ALLOWED_PORTS:
            raise FetchPolicyError(f"URL scheme is not allowed: {scheme}")

        if url.username is not None or url.password is not None:
            raise FetchPolicyError("URLs containing user information are not allowed")

        raw_hostname = url.host

        if not raw_hostname:
            raise FetchPolicyError("URL must contain a hostname")

        hostname = raw_hostname.removeprefix("[").removesuffix("]").rstrip(".").lower()

        expected_port = _ALLOWED_PORTS[scheme]
        port = url.port or expected_port

        if port != expected_port:
            raise FetchPolicyError(f"Non-standard {scheme} port is not allowed: {port}")

        literal_address = self._parse_ip_literal(hostname)

        addresses: tuple[IPAddress, ...]

        if literal_address is not None:
            addresses = (literal_address,)
        else:
            hostname = self._validate_hostname(hostname)
            addresses = await self._resolver.resolve(hostname)

        if not addresses:
            raise FetchPolicyError("Target resolved to no addresses")

        for address in addresses:
            if not address.is_global:
                raise FetchPolicyError(f"Target resolves to a non-global address: {address}")

        return ValidatedTarget(
            url=url,
            hostname=hostname,
            port=port,
            addresses=addresses,
        )

    @staticmethod
    def _parse_ip_literal(
        hostname: str,
    ) -> IPAddress | None:
        try:
            return ip_address(hostname)
        except ValueError:
            return None

    @staticmethod
    def _validate_hostname(hostname: str) -> str:
        if hostname in _BLOCKED_HOSTNAMES:
            raise FetchPolicyError(f"Hostname is not allowed: {hostname}")

        if hostname.endswith(_BLOCKED_HOSTNAME_SUFFIXES):
            raise FetchPolicyError(f"Hostname is not allowed: {hostname}")

        if "." not in hostname:
            raise FetchPolicyError(f"Single-label hostnames are not allowed: {hostname}")

        try:
            return validate_domain(hostname)
        except ValueError as exc:
            raise FetchPolicyError(f"Hostname is invalid: {hostname}") from exc

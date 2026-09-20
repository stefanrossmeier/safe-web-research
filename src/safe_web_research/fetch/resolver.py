import asyncio
import socket
from collections.abc import Mapping, Sequence
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Protocol

from safe_web_research.fetch.errors import FetchResolutionError

IPAddress = IPv4Address | IPv6Address


class DNSResolver(Protocol):
    """Resolve a hostname into all currently returned IP addresses."""

    async def resolve(self, hostname: str) -> tuple[IPAddress, ...]:
        """Resolve a hostname without applying fetch policy."""
        ...


class SystemDNSResolver:
    """Resolver backed by the operating system resolver."""

    async def resolve(self, hostname: str) -> tuple[IPAddress, ...]:
        normalized = hostname.rstrip(".").lower()

        try:
            records = await asyncio.to_thread(
                socket.getaddrinfo,
                normalized,
                None,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise FetchResolutionError(f"DNS resolution failed for hostname: {normalized}") from exc

        addresses = {ip_address(record[4][0]) for record in records}

        if not addresses:
            raise FetchResolutionError(
                f"DNS resolution returned no addresses for hostname: {normalized}"
            )

        return tuple(
            sorted(
                addresses,
                key=lambda address: (
                    address.version,
                    str(address),
                ),
            )
        )


class FakeDNSResolver:
    """Deterministic DNS resolver for tests."""

    def __init__(
        self,
        addresses_by_hostname: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._addresses_by_hostname = {
            hostname.rstrip(".").lower(): tuple(ip_address(address) for address in addresses)
            for hostname, addresses in (addresses_by_hostname or {}).items()
        }
        self.requests: list[str] = []

    async def resolve(self, hostname: str) -> tuple[IPAddress, ...]:
        normalized = hostname.rstrip(".").lower()
        self.requests.append(normalized)

        try:
            addresses = self._addresses_by_hostname[normalized]
        except KeyError as exc:
            raise FetchResolutionError(
                f"No fake DNS result configured for hostname: {normalized}"
            ) from exc

        if not addresses:
            raise FetchResolutionError(
                f"DNS resolution returned no addresses for hostname: {normalized}"
            )

        return addresses

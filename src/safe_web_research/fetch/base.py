from typing import Protocol

from safe_web_research.domain.fetch import FetchedDocument, FetchRequest


class Fetcher(Protocol):
    """Interface for retrieving one web resource."""

    async def fetch(self, request: FetchRequest) -> FetchedDocument:
        """Fetch one resource and return a normalized document."""
        ...

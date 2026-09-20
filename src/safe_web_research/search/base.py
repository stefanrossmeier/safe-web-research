from typing import Protocol

from safe_web_research.domain.search import SearchRequest, SearchResult


class SearchProvider(Protocol):
    """Provider-neutral interface for web search."""

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        """Return normalized search results for one request."""
        ...

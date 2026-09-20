from collections.abc import Mapping, Sequence

from safe_web_research.domain.search import SearchRequest, SearchResult
from safe_web_research.search.base import SearchProvider


class FakeSearchProvider(SearchProvider):
    """Deterministic in-memory search provider for tests."""

    def __init__(
        self,
        results_by_query: Mapping[str, Sequence[SearchResult]] | None = None,
    ) -> None:
        self._results_by_query = {
            query: [result.model_copy(deep=True) for result in results]
            for query, results in (results_by_query or {}).items()
        }
        self.requests: list[SearchRequest] = []

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        self.requests.append(request.model_copy(deep=True))
        results = self._results_by_query.get(request.query, [])
        return [result.model_copy(deep=True) for result in results[: request.max_results]]

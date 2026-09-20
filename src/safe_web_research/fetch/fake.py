from collections.abc import Mapping

from safe_web_research.domain.fetch import FetchedDocument, FetchRequest
from safe_web_research.fetch.base import Fetcher


class FakeFetcher(Fetcher):
    """Deterministic in-memory fetcher for tests."""

    def __init__(
        self,
        documents_by_url: Mapping[str, FetchedDocument] | None = None,
    ) -> None:
        self._documents_by_url = {
            url: document.model_copy(deep=True)
            for url, document in (documents_by_url or {}).items()
        }
        self.requests: list[FetchRequest] = []

    async def fetch(self, request: FetchRequest) -> FetchedDocument:
        self.requests.append(request.model_copy(deep=True))

        key = str(request.url)

        try:
            document = self._documents_by_url[key]
        except KeyError as exc:
            raise LookupError(f"No fake document configured for URL: {key}") from exc

        return document.model_copy(deep=True)

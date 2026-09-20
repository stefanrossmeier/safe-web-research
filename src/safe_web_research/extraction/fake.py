from collections.abc import Mapping

from safe_web_research.domain.extraction import ExtractedDocument
from safe_web_research.domain.fetch import FetchedDocument
from safe_web_research.extraction.base import Extractor


class FakeExtractor(Extractor):
    """Deterministic in-memory extractor for tests."""

    def __init__(
        self,
        documents_by_url: Mapping[str, ExtractedDocument] | None = None,
    ) -> None:
        self._documents_by_url = {
            url: document.model_copy(deep=True)
            for url, document in (documents_by_url or {}).items()
        }
        self.documents: list[FetchedDocument] = []

    async def extract(self, document: FetchedDocument) -> ExtractedDocument:
        self.documents.append(document.model_copy(deep=True))

        key = str(document.final_url)

        try:
            extracted = self._documents_by_url[key]
        except KeyError as exc:
            raise LookupError(f"No fake extraction configured for URL: {key}") from exc

        return extracted.model_copy(deep=True)

from typing import Protocol

from safe_web_research.domain.extraction import ExtractedDocument
from safe_web_research.domain.fetch import FetchedDocument


class Extractor(Protocol):
    """Interface for converting fetched bytes into normalized evidence."""

    async def extract(self, document: FetchedDocument) -> ExtractedDocument:
        """Extract normalized source metadata and evidence chunks."""
        ...

from pydantic import Field

from safe_web_research.domain.base import StrictModel
from safe_web_research.domain.evidence import EvidenceChunk, Source


class ExtractedDocument(StrictModel):
    """Normalized content extracted from one fetched source."""

    source: Source
    chunks: list[EvidenceChunk] = Field(default_factory=list)

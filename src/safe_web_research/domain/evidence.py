from datetime import datetime

from pydantic import Field, HttpUrl

from safe_web_research.domain.base import StrictModel


class Source(StrictModel):
    """A web source used by the research process."""

    source_id: str = Field(min_length=1)

    url: HttpUrl
    title: str

    provider: str = Field(min_length=1)

    retrieved_at: datetime
    published_at: datetime | None = None

    content_hash: str = Field(
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 hash of normalized source content.",
    )


class EvidenceChunk(StrictModel):
    """A bounded piece of extracted source material."""

    chunk_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)

    text: str = Field(min_length=1)

    position: int = Field(
        ge=0,
        description="Zero-based chunk position within the source.",
    )

from datetime import datetime

from pydantic import Field, HttpUrl

from safe_web_research.domain.base import StrictModel, utc_now


class FetchRequest(StrictModel):
    """Request to retrieve one validated web resource."""

    url: HttpUrl


class FetchedDocument(StrictModel):
    """Raw result returned by the bounded fetch layer."""

    requested_url: HttpUrl
    final_url: HttpUrl

    status_code: int = Field(ge=100, le=599)
    content_type: str = Field(min_length=1)

    body: bytes

    redirect_chain: list[HttpUrl] = Field(default_factory=list)

    retrieved_at: datetime = Field(default_factory=utc_now)

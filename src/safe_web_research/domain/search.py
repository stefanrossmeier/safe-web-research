from datetime import datetime

from pydantic import Field, HttpUrl

from safe_web_research.domain.base import StrictModel, utc_now


class SearchRequest(StrictModel):
    """Provider-neutral request for web search results."""

    query: str = Field(min_length=1, max_length=1000)
    max_results: int = Field(default=10, ge=1, le=20)
    freshness_days: int | None = Field(default=None, ge=1)

    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)

    language: str | None = Field(default=None, min_length=2, max_length=16)
    country: str | None = Field(default=None, min_length=2, max_length=16)


class SearchResult(StrictModel):
    """Normalized result returned by any search provider."""

    result_id: str = Field(min_length=1)
    url: HttpUrl
    title: str = Field(max_length=1000)
    snippet: str = Field(max_length=10_000)

    rank: int = Field(ge=1)
    provider: str = Field(min_length=1)

    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)

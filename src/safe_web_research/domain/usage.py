from pydantic import Field

from safe_web_research.domain.base import StrictModel


class ResearchBudget(StrictModel):
    """Hard upper bounds for one research operation."""

    max_searches: int = Field(default=10, ge=0, le=100)
    max_fetch_attempts: int = Field(default=40, ge=0, le=500)
    max_pages: int = Field(default=20, ge=0, le=100)

    max_bytes_per_page: int = Field(
        default=5_000_000,
        ge=0,
        le=50_000_000,
    )
    max_total_bytes: int = Field(
        default=50_000_000,
        ge=0,
        le=250_000_000,
    )

    max_redirects: int = Field(default=5, ge=0, le=20)

    max_llm_calls: int = Field(default=10, ge=0, le=100)
    max_input_tokens: int = Field(default=500_000, ge=0, le=5_000_000)
    max_output_tokens: int = Field(default=50_000, ge=0, le=500_000)


class ResearchUsage(StrictModel):
    """Resources consumed by one research operation."""

    search_requests: int = Field(default=0, ge=0)

    fetch_attempts: int = Field(default=0, ge=0)
    pages_fetched: int = Field(default=0, ge=0)
    bytes_fetched: int = Field(default=0, ge=0)

    llm_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    estimated_cost_usd: float = Field(default=0.0, ge=0)

from typing import Literal

from pydantic import Field

from safe_web_research.domain.base import StrictModel


class ResearchQualityCase(StrictModel):
    case_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    question: str = Field(min_length=1)
    allowed_domains: list[str] = Field(min_length=1)
    expected_terms: list[str] = Field(min_length=1)


class ResearchQualitySuite(StrictModel):
    version: Literal["1"] = "1"
    cases: list[ResearchQualityCase] = Field(min_length=1)


class ResearchQualityCaseResult(StrictModel):
    case_id: str
    category: str
    passed: bool
    answer_present: bool
    expected_terms_found: int
    expected_terms_total: int
    claims: int
    verified_claims: int
    supported_claims: int
    partial_claims: int
    unsupported_claims: int
    contradicted_claims: int
    hard_limit_flags: list[str]
    incomplete_reasons: list[str]
    search_requests: int
    fetch_attempts: int
    pages_fetched: int
    bytes_fetched: int
    llm_calls: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    seconds: float


class ResearchQualityRun(StrictModel):
    benchmark: Literal["live-research-quality"] = "live-research-quality"
    benchmark_version: Literal["1"] = "1"
    timestamp_utc: str
    git_commit: str
    git_dirty: bool
    model: str
    case_file: str
    cases: list[ResearchQualityCaseResult]
    passed_cases: int
    total_cases: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_pages_fetched: int
    total_fetch_attempts: int
    total_seconds: float

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from benchmarks.research_quality.models import (
    ResearchQualityCase,
    ResearchQualityCaseResult,
    ResearchQualityRun,
    ResearchQualitySuite,
)
from safe_web_research.domain import ClaimSupport, ResearchBudget, ResearchRequest, ResearchResult
from safe_web_research.extraction import WebExtractor
from safe_web_research.fetch import SafeFetcher, SystemDNSResolver, URLPolicy
from safe_web_research.llm import OpenRouterLLMProvider
from safe_web_research.research import (
    EvidenceGatherer,
    ResearchPlanner,
    ResearchService,
    ResearchSynthesizer,
    ResearchVerifier,
)
from safe_web_research.search import BraveSearchProvider

_HARD_LIMIT_FLAGS = frozenset(
    {
        "max_searches_reached",
        "max_fetch_attempts_reached",
        "max_pages_reached",
        "max_total_bytes_reached",
        "max_input_tokens_reached",
        "verification_skipped_llm_budget",
        "evidence_truncated_for_synthesis",
        "no_evidence",
    }
)

_QUALITY_BUDGET = ResearchBudget(
    max_searches=3,
    max_fetch_attempts=12,
    max_pages=6,
    max_bytes_per_page=2_000_000,
    max_total_bytes=8_000_000,
    max_redirects=4,
    max_llm_calls=3,
    max_input_tokens=150_000,
    max_output_tokens=20_000,
)


def _build_service(
    *,
    brave_api_key: str,
    openrouter_api_key: str,
    model: str,
) -> ResearchService:
    llm = OpenRouterLLMProvider(openrouter_api_key, model=model)
    return ResearchService(
        ResearchPlanner(llm),
        EvidenceGatherer(
            BraveSearchProvider(brave_api_key),
            SafeFetcher(URLPolicy(SystemDNSResolver())),
            WebExtractor(),
        ),
        ResearchSynthesizer(llm),
        ResearchVerifier(llm),
    )


def evaluate_case(
    case: ResearchQualityCase,
    result: ResearchResult,
    *,
    seconds: float,
) -> ResearchQualityCaseResult:
    searchable_text = "\n".join(
        [result.answer, *(claim.text for claim in result.claims)]
    ).casefold()
    expected_terms_found = sum(
        1 for term in case.expected_terms if term.casefold() in searchable_text
    )

    supported = sum(
        1 for item in result.claim_verifications if item.verdict == ClaimSupport.SUPPORTED
    )
    partial = sum(1 for item in result.claim_verifications if item.verdict == ClaimSupport.PARTIAL)
    unsupported = sum(
        1 for item in result.claim_verifications if item.verdict == ClaimSupport.UNSUPPORTED
    )
    contradicted = sum(
        1 for item in result.claim_verifications if item.verdict == ClaimSupport.CONTRADICTED
    )

    hard_limit_flags = [
        reason for reason in result.incomplete_reasons if reason in _HARD_LIMIT_FLAGS
    ]
    claims = len(result.claims)
    verified_claims = len(result.claim_verifications)

    verification_complete = claims > 0 and verified_claims == claims
    support_acceptable = verified_claims > 0 and unsupported == 0 and contradicted == 0

    passed = (
        bool(result.answer)
        and expected_terms_found == len(case.expected_terms)
        and verification_complete
        and support_acceptable
        and not hard_limit_flags
    )

    usage = result.usage
    return ResearchQualityCaseResult(
        case_id=case.case_id,
        category=case.category,
        passed=passed,
        answer_present=bool(result.answer),
        expected_terms_found=expected_terms_found,
        expected_terms_total=len(case.expected_terms),
        claims=claims,
        verified_claims=verified_claims,
        supported_claims=supported,
        partial_claims=partial,
        unsupported_claims=unsupported,
        contradicted_claims=contradicted,
        hard_limit_flags=hard_limit_flags,
        incomplete_reasons=result.incomplete_reasons,
        search_requests=usage.search_requests,
        fetch_attempts=usage.fetch_attempts,
        pages_fetched=usage.pages_fetched,
        bytes_fetched=usage.bytes_fetched,
        llm_calls=usage.llm_calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        estimated_cost_usd=usage.estimated_cost_usd,
        seconds=seconds,
    )


async def run_suite(
    suite: ResearchQualitySuite,
    *,
    brave_api_key: str,
    openrouter_api_key: str,
    model: str,
    git_commit: str,
    git_dirty: bool,
    case_file: str,
) -> ResearchQualityRun:
    service = _build_service(
        brave_api_key=brave_api_key,
        openrouter_api_key=openrouter_api_key,
        model=model,
    )

    case_results: list[ResearchQualityCaseResult] = []
    started = perf_counter()

    for case in suite.cases:
        case_started = perf_counter()
        result = await service.research(
            ResearchRequest(
                question=case.question,
                allowed_domains=case.allowed_domains,
                budget=_QUALITY_BUDGET,
            )
        )
        elapsed = perf_counter() - case_started
        case_results.append(evaluate_case(case, result, seconds=elapsed))

    total_seconds = perf_counter() - started

    return ResearchQualityRun(
        timestamp_utc=datetime.now(UTC).isoformat(),
        git_commit=git_commit,
        git_dirty=git_dirty,
        model=model,
        case_file=case_file,
        cases=case_results,
        passed_cases=sum(1 for item in case_results if item.passed),
        total_cases=len(case_results),
        total_cost_usd=sum(item.estimated_cost_usd for item in case_results),
        total_input_tokens=sum(item.input_tokens for item in case_results),
        total_output_tokens=sum(item.output_tokens for item in case_results),
        total_pages_fetched=sum(item.pages_fetched for item in case_results),
        total_fetch_attempts=sum(item.fetch_attempts for item in case_results),
        total_seconds=total_seconds,
    )

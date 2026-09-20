import os

import pytest

from safe_web_research.domain import (
    ResearchBudget,
    ResearchRequest,
)
from safe_web_research.extraction import (
    WebExtractor,
)
from safe_web_research.fetch import (
    SafeFetcher,
    SystemDNSResolver,
    URLPolicy,
)
from safe_web_research.llm import (
    OpenRouterLLMProvider,
)
from safe_web_research.research import (
    EvidenceGatherer,
    ResearchPlanner,
    ResearchService,
    ResearchSynthesizer,
    ResearchVerifier,
)
from safe_web_research.search import (
    BraveSearchProvider,
)


@pytest.mark.live
@pytest.mark.asyncio
async def test_research_service_live_end_to_end() -> None:
    brave_api_key = os.getenv("BRAVE_API_KEY")

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    model = os.getenv("OPENROUTER_TEST_MODEL")

    if not brave_api_key:
        pytest.skip("BRAVE_API_KEY is not configured")

    if not openrouter_api_key:
        pytest.skip("OPENROUTER_API_KEY is not configured")

    if not model:
        pytest.skip("OPENROUTER_TEST_MODEL is not configured")

    llm = OpenRouterLLMProvider(
        openrouter_api_key,
        model=model,
    )

    gatherer = EvidenceGatherer(
        BraveSearchProvider(brave_api_key),
        SafeFetcher(URLPolicy(SystemDNSResolver())),
        WebExtractor(max_chunk_chars=2_500),
    )

    service = ResearchService(
        ResearchPlanner(llm),
        gatherer,
        ResearchSynthesizer(
            llm,
            max_evidence_chars=30_000,
        ),
        ResearchVerifier(
            llm,
            # Verification wraps cited evidence with claim and source metadata,
            # so it needs bounded headroom above the synthesis evidence cap.
            max_evidence_chars=60_000,
        ),
    )

    result = await service.research(
        ResearchRequest(
            question=(
                "According to python.org, "
                "what is Python 3.15.0rc2 "
                "and what does that release "
                "page say about it?"
            ),
            allowed_domains=["python.org"],
            budget=ResearchBudget(
                max_searches=2,
                max_fetch_attempts=6,
                max_pages=2,
                max_bytes_per_page=500_000,
                max_total_bytes=800_000,
                max_redirects=3,
                max_llm_calls=3,
                max_input_tokens=20_000,
                max_output_tokens=10_000,
            ),
        )
    )

    assert result.answer.strip()
    assert result.claims
    assert result.sources
    assert result.evidence

    assert result.usage.search_requests >= 1

    assert result.usage.pages_fetched >= 1

    assert result.usage.llm_calls == 3

    assert result.usage.input_tokens > 0

    assert result.usage.output_tokens > 0

    evidence_ids = {evidence.chunk_id for evidence in result.evidence}

    assert all(set(claim.evidence_ids) <= evidence_ids for claim in result.claims)

    assert len(result.claim_verifications) == len(result.claims)

    claim_ids = {claim.claim_id for claim in result.claims}

    assert {verification.claim_id for verification in result.claim_verifications} == claim_ids

    assert all(
        set(verification.supporting_evidence_ids) <= evidence_ids
        for verification in result.claim_verifications
    )

    assert all(
        (source.url.host or "") == "python.org" or (source.url.host or "").endswith(".python.org")
        for source in result.sources
    )

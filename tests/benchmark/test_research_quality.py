from pathlib import Path

from benchmarks.research_quality.models import ResearchQualityCase, ResearchQualitySuite
from benchmarks.research_quality.reporting import render_markdown
from benchmarks.research_quality.runner import evaluate_case
from safe_web_research.domain import (
    Claim,
    ClaimSupport,
    ClaimVerification,
    ResearchResult,
    ResearchUsage,
)

_ROOT = Path(__file__).resolve().parents[2]
_CASES = _ROOT / "benchmarks" / "research-quality" / "cases.json"


def test_research_quality_case_matrix_loads_and_is_diverse() -> None:
    suite = ResearchQualitySuite.model_validate_json(_CASES.read_text(encoding="utf-8"))

    assert len(suite.cases) == 5
    assert len({case.case_id for case in suite.cases}) == 5
    assert len({case.category for case in suite.cases}) >= 4


def test_research_quality_case_passes_with_verified_supported_claims() -> None:
    case = ResearchQualityCase(
        case_id="example",
        category="docs",
        question="question",
        allowed_domains=["example.com"],
        expected_terms=["UTF-8"],
    )
    result = ResearchResult(
        answer="The default is UTF-8.",
        claims=[
            Claim(
                claim_id="claim-1",
                text="The default is UTF-8.",
                evidence_ids=["evidence-1"],
                confidence=0.9,
            )
        ],
        claim_verifications=[
            ClaimVerification(
                claim_id="claim-1",
                verdict=ClaimSupport.SUPPORTED,
                confidence=0.95,
                supporting_evidence_ids=["evidence-1"],
                explanation="Supported by the cited evidence.",
            )
        ],
        usage=ResearchUsage(
            pages_fetched=3,
            input_tokens=1_000,
            output_tokens=200,
            estimated_cost_usd=0.01,
        ),
    )

    evaluated = evaluate_case(case, result, seconds=1.25)

    assert evaluated.passed
    assert evaluated.expected_terms_found == 1
    assert evaluated.verified_claims == 1
    assert evaluated.hard_limit_flags == []


def test_research_quality_case_fails_on_hard_limit_flag() -> None:
    case = ResearchQualityCase(
        case_id="example",
        category="docs",
        question="question",
        allowed_domains=["example.com"],
        expected_terms=["UTF-8"],
    )
    result = ResearchResult(
        answer="The default is UTF-8.",
        claims=[
            Claim(
                claim_id="claim-1",
                text="The default is UTF-8.",
                evidence_ids=["evidence-1"],
                confidence=0.9,
            )
        ],
        claim_verifications=[
            ClaimVerification(
                claim_id="claim-1",
                verdict=ClaimSupport.PARTIAL,
                confidence=0.8,
                supporting_evidence_ids=["evidence-1"],
                explanation="Partially supported.",
            )
        ],
        incomplete_reasons=["max_pages_reached"],
    )

    evaluated = evaluate_case(case, result, seconds=1.0)

    assert not evaluated.passed
    assert evaluated.hard_limit_flags == ["max_pages_reached"]


def test_research_quality_markdown_states_live_limitations() -> None:
    from benchmarks.research_quality.models import ResearchQualityRun

    run = ResearchQualityRun(
        timestamp_utc="2026-09-20T12:00:00+00:00",
        git_commit="abc123",
        git_dirty=False,
        model="z-ai/glm-5.3-flash",
        case_file="benchmarks/research-quality/cases.json",
        cases=[],
        passed_cases=0,
        total_cases=0,
        total_cost_usd=0.0,
        total_input_tokens=0,
        total_output_tokens=0,
        total_pages_fetched=0,
        total_fetch_attempts=0,
        total_seconds=0.0,
    )

    markdown = render_markdown(run)

    assert "live provider/network quality matrix" in markdown
    assert "not a security benchmark" in markdown
    assert "not a complete semantic answer-quality score" in markdown

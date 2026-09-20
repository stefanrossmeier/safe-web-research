import argparse
import asyncio
import os
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from safe_web_research.domain import (
    ResearchBudget,
    ResearchRequest,
    ResearchResult,
)
from safe_web_research.extraction import WebExtractor
from safe_web_research.fetch import (
    SafeFetcher,
    SystemDNSResolver,
    URLPolicy,
)
from safe_web_research.llm import OpenRouterLLMProvider
from safe_web_research.research import (
    EvidenceGatherer,
    ResearchError,
    ResearchPlanner,
    ResearchService,
    ResearchSynthesizer,
    ResearchVerifier,
)
from safe_web_research.search import BraveSearchProvider

_DEFAULT_MODEL = "openai/gpt-5-mini"
_DEFAULT_BUDGET = ResearchBudget()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="safe-web-research",
        description=("Bounded, provenance-aware web research with SSRF-resistant fetching."),
    )

    parser.add_argument(
        "--version",
        action="version",
        version="safe-web-research 0.1.0",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    research = subparsers.add_parser(
        "research",
        help="Run one bounded web research request.",
    )

    research.add_argument(
        "question",
        help="Research question.",
    )

    research.add_argument(
        "--domain",
        dest="allowed_domains",
        action="append",
        default=[],
        help="Restrict search to a domain. Repeatable.",
    )

    research.add_argument(
        "--block-domain",
        dest="blocked_domains",
        action="append",
        default=[],
        help="Exclude a domain from search. Repeatable.",
    )

    research.add_argument(
        "--freshness-days",
        type=int,
        default=None,
        help="Restrict search to approximately the last N days.",
    )

    research.add_argument(
        "--language",
        default=None,
        help="Search language code.",
    )

    research.add_argument(
        "--country",
        default=None,
        help="Search country code.",
    )

    research.add_argument(
        "--model",
        default=os.getenv(
            "OPENROUTER_MODEL",
            _DEFAULT_MODEL,
        ),
        help=(f"OpenRouter model slug. Defaults to OPENROUTER_MODEL or {_DEFAULT_MODEL}."),
    )

    research.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip the semantic claim-support verification pass.",
    )

    research.add_argument(
        "--json",
        action="store_true",
        help="Emit the complete ResearchResult as JSON.",
    )

    research.add_argument(
        "--max-searches",
        type=int,
        default=_DEFAULT_BUDGET.max_searches,
    )
    research.add_argument(
        "--max-fetch-attempts",
        type=int,
        default=_DEFAULT_BUDGET.max_fetch_attempts,
    )
    research.add_argument(
        "--max-pages",
        type=int,
        default=_DEFAULT_BUDGET.max_pages,
    )
    research.add_argument(
        "--max-bytes-per-page",
        type=int,
        default=_DEFAULT_BUDGET.max_bytes_per_page,
    )
    research.add_argument(
        "--max-total-bytes",
        type=int,
        default=_DEFAULT_BUDGET.max_total_bytes,
    )
    research.add_argument(
        "--max-redirects",
        type=int,
        default=_DEFAULT_BUDGET.max_redirects,
    )
    research.add_argument(
        "--max-llm-calls",
        type=int,
        default=_DEFAULT_BUDGET.max_llm_calls,
    )
    research.add_argument(
        "--max-input-tokens",
        type=int,
        default=_DEFAULT_BUDGET.max_input_tokens,
    )
    research.add_argument(
        "--max-output-tokens",
        type=int,
        default=_DEFAULT_BUDGET.max_output_tokens,
    )

    return parser


def _build_service(
    *,
    brave_api_key: str,
    openrouter_api_key: str,
    model: str,
    verify: bool,
) -> ResearchService:
    llm = OpenRouterLLMProvider(
        openrouter_api_key,
        model=model,
    )

    verifier = ResearchVerifier(llm) if verify else None

    return ResearchService(
        ResearchPlanner(llm),
        EvidenceGatherer(
            BraveSearchProvider(brave_api_key),
            SafeFetcher(URLPolicy(SystemDNSResolver())),
            WebExtractor(),
        ),
        ResearchSynthesizer(llm),
        verifier,
    )


def _render_human(
    result: ResearchResult,
) -> str:
    lines: list[str] = []

    lines.append("Answer")
    lines.append("======")
    lines.append(result.answer if result.answer else "No synthesized answer was produced.")

    verification_by_claim = {item.claim_id: item for item in result.claim_verifications}

    if result.claims:
        lines.extend(
            [
                "",
                "Claims",
                "======",
            ]
        )

        for claim in result.claims:
            verification = verification_by_claim.get(claim.claim_id)

            if verification is None:
                support_label = "unverified"
            else:
                support_label = f"{verification.verdict.value} ({verification.confidence:.2f})"

            lines.append(f"- [{support_label}] {claim.text}")
            lines.append("  evidence: " + ", ".join(claim.evidence_ids))

            if verification is not None:
                if verification.supporting_evidence_ids:
                    lines.append("  supporting: " + ", ".join(verification.supporting_evidence_ids))

                lines.append("  verification: " + verification.explanation)

    if result.sources:
        lines.extend(
            [
                "",
                "Sources",
                "=======",
            ]
        )

        for source in result.sources:
            lines.append(f"- {source.title or source.source_id} — {source.url}")

    if result.conflicts:
        lines.extend(
            [
                "",
                "Conflicts",
                "=========",
            ]
        )

        for conflict in result.conflicts:
            lines.append(f"- {conflict.description}")

    if result.security_events:
        lines.extend(
            [
                "",
                "Security events",
                "===============",
            ]
        )

        for event in result.security_events:
            lines.append(f"- [{event.severity.value}] {event.event_type.value}: {event.message}")

    if result.incomplete_reasons:
        lines.extend(
            [
                "",
                "Incomplete / quality flags",
                "==========================",
            ]
        )

        for reason in result.incomplete_reasons:
            lines.append(f"- {reason}")

    usage = result.usage

    lines.extend(
        [
            "",
            "Usage",
            "=====",
            f"search requests: {usage.search_requests}",
            f"fetch attempts: {usage.fetch_attempts}",
            f"pages fetched: {usage.pages_fetched}",
            f"bytes fetched: {usage.bytes_fetched}",
            f"LLM calls: {usage.llm_calls}",
            f"input tokens: {usage.input_tokens}",
            f"output tokens: {usage.output_tokens}",
            f"estimated cost USD: {usage.estimated_cost_usd:.6f}",
        ]
    )

    return "\n".join(lines)


async def _run_research(
    args: argparse.Namespace,
) -> ResearchResult:
    brave_api_key = os.getenv("BRAVE_API_KEY")

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    missing: list[str] = []

    if not brave_api_key:
        missing.append("BRAVE_API_KEY")

    if not openrouter_api_key:
        missing.append("OPENROUTER_API_KEY")

    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))

    # The combined validation above rejects both None and empty strings.
    # These assertions narrow Optional[str] to str for mypy.
    assert brave_api_key is not None
    assert openrouter_api_key is not None

    budget = ResearchBudget(
        max_searches=args.max_searches,
        max_fetch_attempts=args.max_fetch_attempts,
        max_pages=args.max_pages,
        max_bytes_per_page=args.max_bytes_per_page,
        max_total_bytes=args.max_total_bytes,
        max_redirects=args.max_redirects,
        max_llm_calls=args.max_llm_calls,
        max_input_tokens=args.max_input_tokens,
        max_output_tokens=args.max_output_tokens,
    )

    request = ResearchRequest(
        question=args.question,
        budget=budget,
        allowed_domains=args.allowed_domains,
        blocked_domains=args.blocked_domains,
        freshness_days=args.freshness_days,
        language=args.language,
        country=args.country,
    )

    service = _build_service(
        brave_api_key=brave_api_key,
        openrouter_api_key=openrouter_api_key,
        model=args.model,
        verify=not args.no_verify,
    )

    return await service.research(request)


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "research":
        parser.error("Unsupported command")

    try:
        result = asyncio.run(_run_research(args))
    except (
        ResearchError,
        ValidationError,
        RuntimeError,
    ) as exc:
        print(
            f"error: {exc}",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print(
            "error: interrupted",
            file=sys.stderr,
        )
        return 130

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        print(_render_human(result))

    return 0 if result.answer else 1

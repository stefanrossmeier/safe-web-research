from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

from benchmarks.agent_usage.models import (
    AgentUsageCase,
    AgentUsageCaseResult,
    AgentUsageRun,
    AgentUsageSuite,
)
from examples.research_agent.agent import ResearchAgent
from examples.research_agent.models import ResearchAgentRun


def _timings(run: ResearchAgentRun) -> dict[str, float]:
    outer_model_seconds = sum(item.seconds for item in run.model_calls)
    research_tool_seconds = sum(item.seconds for item in run.tool_calls)
    search_provider_seconds = sum(
        call.seconds for tool_call in run.tool_calls for call in tool_call.search_calls
    )
    fetch_seconds = sum(
        call.seconds for tool_call in run.tool_calls for call in tool_call.fetch_calls
    )
    research_llm_seconds = sum(
        call.seconds for tool_call in run.tool_calls for call in tool_call.research_llm_calls
    )
    # Content judgement calls are concurrent within one research operation. Summing all
    # Jev call durations would overstate wall time, so use the slowest judgement in each
    # tool call as the approximate critical path for that phase.
    judgement_critical_path_seconds = sum(
        max((call.seconds for call in tool_call.judgement_calls), default=0.0)
        for tool_call in run.tool_calls
    )
    attributed_research = (
        search_provider_seconds
        + fetch_seconds
        + research_llm_seconds
        + judgement_critical_path_seconds
    )
    unattributed_research_seconds = max(0.0, research_tool_seconds - attributed_research)
    return {
        "outer_model_seconds": outer_model_seconds,
        "research_tool_seconds": research_tool_seconds,
        "search_provider_seconds": search_provider_seconds,
        "fetch_seconds": fetch_seconds,
        "research_llm_seconds": research_llm_seconds,
        "judgement_critical_path_seconds": judgement_critical_path_seconds,
        "unattributed_research_seconds": unattributed_research_seconds,
    }


def evaluate_case(case: AgentUsageCase, run: ResearchAgentRun) -> AgentUsageCaseResult:
    successful = [item for item in run.tool_calls if item.ok and item.observation is not None]
    rejected = [item for item in run.tool_calls if not item.ok]
    capabilities_used = sorted({item.capability.value for item in successful})
    expected_capabilities = sorted(item.value for item in case.expected_capabilities)
    capability_pass = set(expected_capabilities).issubset(set(capabilities_used))

    source_urls = {
        source.url
        for item in successful
        for source in item.observation.sources
        if item.observation is not None
    }
    answer_casefold = run.final_answer.casefold()
    cited_sources = sum(1 for url in source_urls if url in run.final_answer)
    expected_terms_found = sum(
        1 for term in case.expected_terms if term.casefold() in answer_casefold
    )

    tool_call_pass = len(successful) >= case.min_tool_calls and not rejected
    search_pass = run.search_requests >= case.min_search_requests
    source_pass = len(source_urls) >= case.min_sources
    citation_pass = cited_sources >= case.min_cited_sources
    expected_terms_pass = expected_terms_found == len(case.expected_terms)
    answer_present = bool(run.final_answer.strip())
    has_error = run.error_type is not None

    checks = {
        "answer_present": answer_present,
        "capability_profile": capability_pass,
        "tool_calls_no_rejections": tool_call_pass,
        "search_count": search_pass,
        "source_count": source_pass,
        "citation_count": citation_pass,
        "expected_terms": expected_terms_pass,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    if has_error:
        failed_checks.insert(0, "runtime_error")
    passed = not has_error and not failed_checks
    outcome = "error" if has_error else ("pass" if passed else "fail")
    timings = _timings(run)

    return AgentUsageCaseResult(
        case_id=case.case_id,
        category=case.category,
        outcome=outcome,
        passed=passed,
        failed_checks=failed_checks,
        answer_present=answer_present,
        capability_pass=capability_pass,
        tool_call_pass=tool_call_pass,
        search_pass=search_pass,
        source_pass=source_pass,
        citation_pass=citation_pass,
        expected_terms_pass=expected_terms_pass,
        expected_capabilities=expected_capabilities,
        capabilities_used=capabilities_used,
        successful_tool_calls=len(successful),
        rejected_tool_calls=len(rejected),
        search_requests=run.search_requests,
        search_provider_errors=run.search_provider_errors,
        fetch_attempts=run.fetch_attempts,
        pages_fetched=run.pages_fetched,
        unique_sources=len(source_urls),
        cited_sources=cited_sources,
        expected_terms_found=expected_terms_found,
        expected_terms_total=len(case.expected_terms),
        agent_input_tokens=run.agent_input_tokens,
        agent_output_tokens=run.agent_output_tokens,
        research_input_tokens=run.research_input_tokens,
        research_output_tokens=run.research_output_tokens,
        agent_cost_usd=run.agent_cost_usd,
        research_cost_usd=run.research_cost_usd,
        tracked_cost_usd=run.tracked_cost_usd,
        judgement_calls=run.judgement_calls,
        redundant_research_calls_prevented=run.redundant_research_calls_prevented,
        time_to_first_research_result_seconds=run.time_to_first_research_result_seconds,
        total_seconds=run.total_seconds,
        error_type=run.error_type,
        error_message=run.error_message,
        trace=run,
        **timings,
    )


def _unexpected_error_run(
    case: AgentUsageCase,
    *,
    agent_model: str,
    research_model: str,
    elapsed: float,
    exc: Exception,
) -> ResearchAgentRun:
    return ResearchAgentRun(
        task=case.task,
        agent_model=agent_model,
        research_model=research_model,
        final_answer="",
        model_calls=[],
        tool_calls=[],
        total_seconds=elapsed,
        time_to_first_research_result_seconds=None,
        agent_input_tokens=0,
        agent_output_tokens=0,
        agent_cost_usd=0.0,
        research_input_tokens=0,
        research_output_tokens=0,
        research_cost_usd=0.0,
        judgement_calls=0,
        search_requests=0,
        search_provider_errors=0,
        fetch_attempts=0,
        pages_fetched=0,
        tracked_cost_usd=0.0,
        error_type=type(exc).__name__,
        error_message=str(exc),
    )


async def run_suite(
    suite: AgentUsageSuite,
    *,
    agent: ResearchAgent,
    git_commit: str,
    git_dirty: bool,
    case_file: str,
    agent_model: str,
    research_model: str,
    research_profile: str,
) -> AgentUsageRun:
    results: list[AgentUsageCaseResult] = []
    started = perf_counter()
    total = len(suite.cases)

    for index, case in enumerate(suite.cases, start=1):
        print(f"[{index}/{total}] {case.case_id} ...", flush=True)
        case_started = perf_counter()
        try:
            run = await agent.run(case.task)
        except Exception as exc:  # benchmark isolation: record one case, continue the suite
            run = _unexpected_error_run(
                case,
                agent_model=agent_model,
                research_model=research_model,
                elapsed=perf_counter() - case_started,
                exc=exc,
            )

        result = evaluate_case(case, run)
        results.append(result)
        suffix = ""
        if result.error_type is not None:
            suffix = f" ({result.error_type}: {result.error_message})"
        elif result.failed_checks:
            suffix = " [failed: " + ", ".join(result.failed_checks) + "]"
        print(
            f"[{index}/{total}] {case.case_id}: {result.outcome.upper()} "
            f"{result.total_seconds:.2f}s, ${result.tracked_cost_usd:.6f}{suffix}",
            flush=True,
        )

    total_seconds = perf_counter() - started

    return AgentUsageRun(
        timestamp_utc=datetime.now(UTC).isoformat(),
        git_commit=git_commit,
        git_dirty=git_dirty,
        agent_model=agent_model,
        research_model=research_model,
        research_profile=research_profile,
        case_file=case_file,
        cases=results,
        passed_cases=sum(1 for item in results if item.passed),
        error_cases=sum(1 for item in results if item.outcome == "error"),
        total_cases=len(results),
        total_tool_calls=sum(item.successful_tool_calls for item in results),
        total_search_requests=sum(item.search_requests for item in results),
        total_search_provider_errors=sum(item.search_provider_errors for item in results),
        total_fetch_attempts=sum(item.fetch_attempts for item in results),
        total_pages_fetched=sum(item.pages_fetched for item in results),
        total_judgement_calls=sum(item.judgement_calls for item in results),
        total_redundant_research_calls_prevented=sum(
            item.redundant_research_calls_prevented for item in results
        ),
        total_agent_input_tokens=sum(item.agent_input_tokens for item in results),
        total_agent_output_tokens=sum(item.agent_output_tokens for item in results),
        total_research_input_tokens=sum(item.research_input_tokens for item in results),
        total_research_output_tokens=sum(item.research_output_tokens for item in results),
        total_agent_cost_usd=sum(item.agent_cost_usd for item in results),
        total_research_cost_usd=sum(item.research_cost_usd for item in results),
        total_tracked_cost_usd=sum(item.tracked_cost_usd for item in results),
        total_outer_model_seconds=sum(item.outer_model_seconds for item in results),
        total_research_tool_seconds=sum(item.research_tool_seconds for item in results),
        total_search_provider_seconds=sum(item.search_provider_seconds for item in results),
        total_fetch_seconds=sum(item.fetch_seconds for item in results),
        total_research_llm_seconds=sum(item.research_llm_seconds for item in results),
        total_judgement_critical_path_seconds=sum(
            item.judgement_critical_path_seconds for item in results
        ),
        total_unattributed_research_seconds=sum(
            item.unattributed_research_seconds for item in results
        ),
        total_seconds=total_seconds,
    )

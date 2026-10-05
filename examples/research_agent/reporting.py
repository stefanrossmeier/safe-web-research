from __future__ import annotations

from examples.research_agent.models import ResearchAgentRun


def _clean_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def render_run(run: ResearchAgentRun) -> str:
    first_result = run.time_to_first_research_result_seconds
    first_result_text = "n/a" if first_result is None else f"{first_result:.2f}s"
    answer = run.final_answer or "(no final answer)"
    outer_model_seconds = sum(item.seconds for item in run.model_calls)
    research_tool_seconds = sum(item.seconds for item in run.tool_calls)
    search_seconds = sum(item.seconds for call in run.tool_calls for item in call.search_calls)
    fetch_seconds = sum(item.seconds for call in run.tool_calls for item in call.fetch_calls)
    research_llm_seconds = sum(
        item.seconds for call in run.tool_calls for item in call.research_llm_calls
    )
    judgement_critical_path_seconds = sum(
        max((item.seconds for item in call.judgement_calls), default=0.0) for call in run.tool_calls
    )
    attributed_research = (
        search_seconds + fetch_seconds + research_llm_seconds + judgement_critical_path_seconds
    )
    unattributed_research = max(0.0, research_tool_seconds - attributed_research)

    lines = [
        "# Research agent result",
        "",
        answer,
        "",
    ]
    if run.error_type is not None:
        lines.extend(
            [
                "## Error",
                "",
                f"- Type: `{run.error_type}`",
                f"- Message: {run.error_message or 'no message'}",
                f"- Failed step: {run.failed_step if run.failed_step is not None else 'n/a'}",
                f"- Failed purpose: {run.failed_purpose or 'n/a'}",
                "",
            ]
        )

    lines.extend(
        [
            "## Measurements",
            "",
            f"- End-to-end wall time: **{run.total_seconds:.2f}s**",
            f"- Time to first completed research result: **{first_result_text}**",
            f"- Outer-agent model calls: **{outer_model_seconds:.2f}s**",
            f"- safe-web-research tool wall time: **{research_tool_seconds:.2f}s**",
            f"  - Brave Search calls: **{search_seconds:.2f}s**",
            f"  - Safe page fetches: **{fetch_seconds:.2f}s**",
            f"  - Inner research LLM calls: **{research_llm_seconds:.2f}s**",
            f"  - Jev critical-path estimate: **{judgement_critical_path_seconds:.2f}s**",
            f"  - Extraction/orchestration/unattributed: **{unattributed_research:.2f}s**",
            f"- Tracked cost: **${run.tracked_cost_usd:.6f}**",
            f"  - outer-agent model: ${run.agent_cost_usd:.6f}",
            f"  - safe-web-research model/Jev calls: ${run.research_cost_usd:.6f}",
            f"- Searches: **{run.search_requests}**",
            f"- Search-provider errors: **{run.search_provider_errors}**",
            f"- Fetch attempts: **{run.fetch_attempts}**",
            f"- Pages fetched: **{run.pages_fetched}**",
            f"- Jev judgement calls: **{run.judgement_calls}**",
            (
                "- Redundant same-scope research calls prevented: "
                f"**{run.redundant_research_calls_prevented}**"
            ),
            (
                "- Outer-agent tokens: "
                f"**{run.agent_input_tokens} in / {run.agent_output_tokens} out**"
            ),
            (
                "- Research tokens: "
                f"**{run.research_input_tokens} in / {run.research_output_tokens} out**"
            ),
            "",
            "## Tool calls",
            "",
            (
                "| # | Capability | Status | Searches | Fetches | Research LLM | Jev | Pages | "
                "Cost | Seconds |"
            ),
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for index, call in enumerate(run.tool_calls, start=1):
        usage = call.observation.usage if call.observation is not None else None
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    call.capability.value,
                    "ok" if call.ok else "rejected",
                    str(len(call.search_calls)),
                    str(len(call.fetch_calls)),
                    str(len(call.research_llm_calls)),
                    str(len(call.judgement_calls)),
                    str(usage.pages_fetched if usage is not None else 0),
                    f"${usage.estimated_cost_usd:.6f}" if usage is not None else "$0.000000",
                    f"{call.seconds:.2f}",
                ]
            )
            + " |"
        )

    search_calls = [
        (call.capability.value, search_call)
        for call in run.tool_calls
        for search_call in call.search_calls
    ]
    if search_calls:
        lines.extend(
            [
                "",
                "## Search attempts",
                "",
                "| Capability | Status | Results | Seconds | Query |",
                "| --- | --- | ---: | ---: | --- |",
            ]
        )
        for capability, search_call in search_calls:
            lines.append(
                "| "
                + " | ".join(
                    [
                        capability,
                        "ok" if search_call.ok else "error",
                        str(search_call.result_count),
                        f"{search_call.seconds:.2f}",
                        _clean_cell(search_call.query),
                    ]
                )
                + " |"
            )

    fetch_calls = [
        (call.capability.value, fetch_call)
        for call in run.tool_calls
        for fetch_call in call.fetch_calls
    ]
    if fetch_calls:
        lines.extend(
            [
                "",
                "## Fetch attempts",
                "",
                "| Capability | Status | Bytes | Seconds | URL |",
                "| --- | --- | ---: | ---: | --- |",
            ]
        )
        for capability, fetch_call in fetch_calls:
            lines.append(
                "| "
                + " | ".join(
                    [
                        capability,
                        "ok" if fetch_call.ok else "error",
                        str(fetch_call.bytes_fetched),
                        f"{fetch_call.seconds:.2f}",
                        _clean_cell(fetch_call.url),
                    ]
                )
                + " |"
            )

    research_llm_calls = [
        (call.capability.value, llm_call)
        for call in run.tool_calls
        for llm_call in call.research_llm_calls
    ]
    if research_llm_calls:
        lines.extend(
            [
                "",
                "## Inner research LLM calls",
                "",
                "| Capability | Purpose | Status | Tokens in/out | Cost | Seconds |",
                "| --- | --- | --- | --- | ---: | ---: |",
            ]
        )
        for capability, llm_call in research_llm_calls:
            usage = llm_call.usage
            tokens = f"{usage.input_tokens}/{usage.output_tokens}" if usage is not None else "n/a"
            cost = f"${usage.estimated_cost_usd:.6f}" if usage is not None else "n/a"
            lines.append(
                "| "
                + " | ".join(
                    [
                        capability,
                        llm_call.purpose,
                        "ok" if llm_call.ok else "error",
                        tokens,
                        cost,
                        f"{llm_call.seconds:.2f}",
                    ]
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "Jev calls are concurrent within one research operation, so the timing summary uses "
            "the slowest Jev call per tool invocation as the phase's critical-path estimate.",
            "",
            "Tracked cost is the cost reported for successful OpenRouter chat completions and "
            "Jev decisions. If an unusable provider response raises before usage is exposed, "
            "that failed request is not included, so error runs are a lower-bound cost. Brave "
            "Search subscription/query charges are not reported by the current search-provider "
            "interface, so search count is recorded separately.",
            "",
        ]
    )
    return "\n".join(lines)

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.agent_usage.models import AgentUsageRun


def _clean_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def render_markdown(run: AgentUsageRun) -> str:
    lines = [
        "# Live agent-usage benchmark",
        "",
        f"- Timestamp (UTC): `{run.timestamp_utc}`",
        f"- Git commit: `{run.git_commit}`",
        f"- Git dirty: `{run.git_dirty}`",
        f"- Outer-agent model: `{run.agent_model}`",
        f"- Research model: `{run.research_model}`",
        f"- Research profile: `{run.research_profile}`",
        f"- Case file: `{run.case_file}`",
        "",
        "## Aggregate",
        "",
        f"- Passed cases: **{run.passed_cases}/{run.total_cases}**",
        f"- Error cases: **{run.error_cases}**",
        f"- Successful safe-web-research calls: **{run.total_tool_calls}**",
        (
            "- Redundant same-scope research calls prevented: "
            f"**{run.total_redundant_research_calls_prevented}**"
        ),
        f"- Brave search requests: **{run.total_search_requests}**",
        f"- Search-provider errors: **{run.total_search_provider_errors}**",
        f"- Fetch attempts: **{run.total_fetch_attempts}**",
        f"- Pages fetched: **{run.total_pages_fetched}**",
        f"- Jev judgement calls: **{run.total_judgement_calls}**",
        f"- Outer-agent cost: **${run.total_agent_cost_usd:.6f}**",
        f"- Research/Jev cost: **${run.total_research_cost_usd:.6f}**",
        f"- Tracked cost: **${run.total_tracked_cost_usd:.6f}**",
        (
            "- Outer-agent tokens: "
            f"**{run.total_agent_input_tokens} in / {run.total_agent_output_tokens} out**"
        ),
        (
            "- Research tokens: "
            f"**{run.total_research_input_tokens} in / "
            f"{run.total_research_output_tokens} out**"
        ),
        f"- Total wall time: **{run.total_seconds:.2f}s**",
        "",
        "### Timing breakdown",
        "",
        f"- Outer-agent model calls: **{run.total_outer_model_seconds:.2f}s**",
        f"- safe-web-research tool wall time: **{run.total_research_tool_seconds:.2f}s**",
        f"  - Brave Search calls: **{run.total_search_provider_seconds:.2f}s**",
        f"  - Safe page fetches: **{run.total_fetch_seconds:.2f}s**",
        f"  - Inner research LLM calls: **{run.total_research_llm_seconds:.2f}s**",
        (f"  - Jev critical-path estimate: **{run.total_judgement_critical_path_seconds:.2f}s**"),
        (
            "  - Extraction/orchestration/unattributed: "
            f"**{run.total_unattributed_research_seconds:.2f}s**"
        ),
        "",
        "## Cases",
        "",
        (
            "| Case | Outcome | Expected capabilities | Used | Tool calls | Rejected | Searches | "
            "Search errors | Sources | Cited | Terms | Cost | First result | Total | "
            "Failed checks |"
        ),
        (
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | ---: | --- |"
        ),
    ]
    for item in run.cases:
        first = item.time_to_first_research_result_seconds
        first_text = "n/a" if first is None else f"{first:.2f}s"
        failed = ", ".join(item.failed_checks) or "—"
        lines.append(
            "| "
            + " | ".join(
                [
                    item.case_id,
                    item.outcome,
                    ", ".join(item.expected_capabilities),
                    ", ".join(item.capabilities_used) or "—",
                    str(item.successful_tool_calls),
                    str(item.rejected_tool_calls),
                    str(item.search_requests),
                    str(item.search_provider_errors),
                    str(item.unique_sources),
                    str(item.cited_sources),
                    f"{item.expected_terms_found}/{item.expected_terms_total}",
                    f"${item.tracked_cost_usd:.6f}",
                    first_text,
                    f"{item.total_seconds:.2f}s",
                    failed,
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Per-case timing",
            "",
            (
                "| Case | Outer LLM | Research tool | Brave search | Fetch | Research LLM | "
                "Jev critical path | Other research | Total |"
            ),
            ("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"),
        ]
    )
    for item in run.cases:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.case_id,
                    f"{item.outer_model_seconds:.2f}s",
                    f"{item.research_tool_seconds:.2f}s",
                    f"{item.search_provider_seconds:.2f}s",
                    f"{item.fetch_seconds:.2f}s",
                    f"{item.research_llm_seconds:.2f}s",
                    f"{item.judgement_critical_path_seconds:.2f}s",
                    f"{item.unattributed_research_seconds:.2f}s",
                    f"{item.total_seconds:.2f}s",
                ]
            )
            + " |"
        )

    search_attempts = [
        (item.case_id, tool_call.capability.value, call)
        for item in run.cases
        for tool_call in item.trace.tool_calls
        for call in tool_call.search_calls
    ]
    if search_attempts:
        lines.extend(
            [
                "",
                "## Search attempts",
                "",
                "| Case | Capability | Status | Results | Seconds | Query |",
                "| --- | --- | --- | ---: | ---: | --- |",
            ]
        )
        for case_id, capability, call in search_attempts:
            lines.append(
                "| "
                + " | ".join(
                    [
                        case_id,
                        capability,
                        "ok" if call.ok else "error",
                        str(call.result_count),
                        f"{call.seconds:.2f}",
                        _clean_cell(call.query),
                    ]
                )
                + " |"
            )

    fetch_attempts = [
        (item.case_id, tool_call.capability.value, call)
        for item in run.cases
        for tool_call in item.trace.tool_calls
        for call in tool_call.fetch_calls
    ]
    if fetch_attempts:
        lines.extend(
            [
                "",
                "## Fetch attempts",
                "",
                "| Case | Capability | Status | Bytes | Seconds | URL |",
                "| --- | --- | --- | ---: | ---: | --- |",
            ]
        )
        for case_id, capability, call in fetch_attempts:
            lines.append(
                "| "
                + " | ".join(
                    [
                        case_id,
                        capability,
                        "ok" if call.ok else "error",
                        str(call.bytes_fetched),
                        f"{call.seconds:.2f}",
                        _clean_cell(call.url),
                    ]
                )
                + " |"
            )

    research_llm_calls = [
        (item.case_id, tool_call.capability.value, call)
        for item in run.cases
        for tool_call in item.trace.tool_calls
        for call in tool_call.research_llm_calls
    ]
    if research_llm_calls:
        lines.extend(
            [
                "",
                "## Inner research LLM calls",
                "",
                "| Case | Capability | Purpose | Status | Tokens in/out | Cost | Seconds |",
                "| --- | --- | --- | --- | --- | ---: | ---: |",
            ]
        )
        for case_id, capability, call in research_llm_calls:
            usage = call.usage
            tokens = f"{usage.input_tokens}/{usage.output_tokens}" if usage is not None else "n/a"
            cost = f"${usage.estimated_cost_usd:.6f}" if usage is not None else "n/a"
            lines.append(
                "| "
                + " | ".join(
                    [
                        case_id,
                        capability,
                        call.purpose,
                        "ok" if call.ok else "error",
                        tokens,
                        cost,
                        f"{call.seconds:.2f}",
                    ]
                )
                + " |"
            )

    judgement_calls = [
        (item.case_id, tool_call.capability.value, call)
        for item in run.cases
        for tool_call in item.trace.tool_calls
        for call in tool_call.judgement_calls
    ]
    if judgement_calls:
        lines.extend(
            [
                "",
                "## Jev judgement calls",
                "",
                "| Case | Capability | Status | Tokens in/out | Cost | Seconds | Source |",
                "| --- | --- | --- | --- | ---: | ---: | --- |",
            ]
        )
        for case_id, capability, call in judgement_calls:
            lines.append(
                "| "
                + " | ".join(
                    [
                        case_id,
                        capability,
                        "ok" if call.ok else "error",
                        f"{call.input_tokens}/{call.output_tokens}",
                        f"${call.cost_usd:.6f}",
                        f"{call.seconds:.2f}",
                        _clean_cell(call.source_url),
                    ]
                )
                + " |"
            )

    search_failures = [
        (item.case_id, call)
        for item in run.cases
        for tool_call in item.trace.tool_calls
        for call in tool_call.search_calls
        if not call.ok
    ]
    if search_failures:
        lines.extend(["", "## Search-provider errors", ""])
        for case_id, call in search_failures:
            lines.append(
                f"- `{case_id}`: `{call.error_type or 'error'}` — "
                f"{call.error_message or 'no message'} (query: `{call.query}`)"
            )

    failed_cases = [item for item in run.cases if item.failed_checks]
    if failed_cases:
        lines.extend(["", "## Failed checks", ""])
        for item in failed_cases:
            lines.append(f"- `{item.case_id}`: {', '.join(item.failed_checks)}")

    errors = [item for item in run.cases if item.error_type is not None]
    if errors:
        lines.extend(["", "## Errors", ""])
        for item in errors:
            lines.append(
                f"- `{item.case_id}`: `{item.error_type}` — {item.error_message or 'no message'}"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "This benchmark measures a complete outer-agent -> safe-web-research -> "
                "final-answer loop. It is intentionally different from the existing "
                "research-quality benchmark, which calls ResearchService directly."
            ),
            (
                "One safe-web-research invocation is already a multi-query, multi-page research "
                "operation. The example prevents a second successful invocation with the same "
                "capability and constraints when the first result is complete; distinct evidence "
                "scopes such as official_sources plus recent_web still produce separate calls."
            ),
            (
                "Timing separates the Brave Search request itself from safe fetching, inner "
                "research LLM calls, and Jev. Jev calls run concurrently inside each research "
                "operation, so the report uses the slowest Jev call per tool invocation as a "
                "critical-path estimate rather than summing concurrent calls."
            ),
            (
                "A case passes when the agent uses the expected bounded capability profile(s), "
                "meets the minimum tool/search/source counts, returns the lightweight answer "
                "anchors, and cites enough URLs that were actually returned by safe-web-research."
            ),
            (
                "Provider or orchestration failures are recorded per case and do not abort the "
                "remaining suite. Failed non-error cases list every failed evaluation check."
            ),
            (
                "Tracked cost includes successful OpenRouter chat-completion usage and Jev "
                "decision cost reported by providers. If a provider returns an unusable completion "
                "and the adapter raises before exposing usage, that failed request cannot "
                "currently be added to tracked cost; runs containing provider errors therefore "
                "report a lower bound."
            ),
            (
                "Brave Search monetary cost is not available through the current search-provider "
                "interface; the benchmark records search-request count separately."
            ),
            (
                "The suite is live and stochastic. Search results, model routing, latency, token "
                "use, and cost can vary. Treat it as integration/performance evidence, not a "
                "model ranking."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_run(run: AgentUsageRun, *, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = run.timestamp_utc.replace("-", "").replace(":", "").split(".", 1)[0]
    stamp = stamp.replace("+0000", "").replace("+00", "") + "Z"
    markdown = render_markdown(run)
    json_text = json.dumps(run.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    timestamped_md = output_dir / f"{stamp}.md"
    timestamped_json = output_dir / f"{stamp}.json"
    latest_md = output_dir / "latest.md"
    latest_json = output_dir / "latest.json"
    timestamped_md.write_text(markdown, encoding="utf-8")
    timestamped_json.write_text(json_text, encoding="utf-8")
    latest_md.write_text(markdown, encoding="utf-8")
    latest_json.write_text(json_text, encoding="utf-8")
    return latest_md, latest_json

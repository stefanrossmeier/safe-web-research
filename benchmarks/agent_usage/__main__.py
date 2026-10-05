from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
from pathlib import Path

from benchmarks.agent_usage.models import AgentUsageSuite
from benchmarks.agent_usage.reporting import write_run
from benchmarks.agent_usage.runner import run_suite
from examples.research_agent.live import AgentResearchProfile, build_live_agent
from safe_web_research.security import ContentJudgementMode
from safe_web_research.security.openrouter_jev import DEFAULT_JEV_MODEL

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CASES = Path(__file__).with_name("cases.json")
_DEFAULT_OUTPUT = _ROOT / "reports" / "agent_usage" / "local"
_DEFAULT_AGENT_MODEL = "openai/gpt-6-luna"
_DEFAULT_RESEARCH_MODEL = "openai/gpt-6-luna"


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_dirty() -> bool:
    return bool(_git_output("status", "--porcelain"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the paid live outer-agent/safe-web-research usage benchmark."
    )
    parser.add_argument(
        "--agent-model",
        default=os.getenv("OPENROUTER_AGENT_MODEL") or _DEFAULT_AGENT_MODEL,
    )
    parser.add_argument(
        "--research-model",
        default=os.getenv("OPENROUTER_MODEL") or _DEFAULT_RESEARCH_MODEL,
    )
    parser.add_argument("--cases", type=Path, default=_DEFAULT_CASES)
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Run only the named case. Repeat to select multiple cases.",
    )
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--max-tool-calls", type=int, default=4)
    parser.add_argument(
        "--research-profile",
        type=AgentResearchProfile,
        choices=list(AgentResearchProfile),
        default=AgentResearchProfile.COMPACT,
        help=(
            "compact bounds evidence/context for agent experiments; full preserves the earlier "
            "more generous research limits"
        ),
    )
    parser.add_argument("--no-verify", action="store_true")
    parser.add_argument(
        "--content-judgement",
        type=ContentJudgementMode,
        choices=list(ContentJudgementMode),
        default=os.getenv(
            "SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT",
            ContentJudgementMode.OBSERVE.value,
        ),
    )
    parser.add_argument(
        "--jev-model",
        default=os.getenv("OPENROUTER_JEV_MODEL", DEFAULT_JEV_MODEL),
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a development run from a dirty tree.",
    )
    args = parser.parse_args()

    brave_api_key = os.getenv("BRAVE_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not brave_api_key or not openrouter_api_key:
        raise SystemExit("BRAVE_API_KEY and OPENROUTER_API_KEY are required")

    dirty = _git_dirty()
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "Refusing to record agent-usage results from a dirty Git tree. "
            "Commit first or use --allow-dirty for a local experiment."
        )

    suite = AgentUsageSuite.model_validate_json(args.cases.read_text(encoding="utf-8"))
    if args.case_id:
        requested = set(args.case_id)
        selected = [case for case in suite.cases if case.case_id in requested]
        found = {case.case_id for case in selected}
        missing = sorted(requested - found)
        if missing:
            raise SystemExit("Unknown --case-id value(s): " + ", ".join(missing))
        suite = AgentUsageSuite(cases=selected)
    case_file = str(args.cases.relative_to(_ROOT))
    commit = _git_output("rev-parse", "--short=12", "HEAD")
    agent = build_live_agent(
        brave_api_key=brave_api_key,
        openrouter_api_key=openrouter_api_key,
        agent_model=args.agent_model,
        research_model=args.research_model,
        max_steps=args.max_steps,
        max_tool_calls=args.max_tool_calls,
        research_profile=args.research_profile,
        verify=not args.no_verify,
        content_judgement_mode=args.content_judgement,
        jev_model=args.jev_model,
    )

    print(
        "This benchmark calls real Brave/OpenRouter providers and may incur charges.\n"
        f"Outer-agent model: {args.agent_model}\n"
        f"Research model: {args.research_model}\n"
        f"Research profile: {args.research_profile.value}\n"
        f"Cases: {len(suite.cases)}"
    )
    run = asyncio.run(
        run_suite(
            suite,
            agent=agent,
            git_commit=commit,
            git_dirty=dirty,
            case_file=case_file,
            agent_model=args.agent_model,
            research_model=args.research_model,
            research_profile=args.research_profile.value,
        )
    )
    latest_md, latest_json = write_run(run, output_dir=args.output_dir)
    print(f"Wrote {latest_md.relative_to(_ROOT)}")
    print(f"Wrote {latest_json.relative_to(_ROOT)}")
    print(f"Passed {run.passed_cases}/{run.total_cases} cases")
    print(f"Error cases: {run.error_cases}")
    print(f"Search requests: {run.total_search_requests}")
    print(f"Search-provider errors: {run.total_search_provider_errors}")
    print(
        "Redundant same-scope research calls prevented: "
        f"{run.total_redundant_research_calls_prevented}"
    )
    print(
        "Timing: "
        f"outer={run.total_outer_model_seconds:.2f}s, "
        f"research={run.total_research_tool_seconds:.2f}s, "
        f"search={run.total_search_provider_seconds:.2f}s, "
        f"fetch={run.total_fetch_seconds:.2f}s, "
        f"research-llm={run.total_research_llm_seconds:.2f}s, "
        f"jev-critical={run.total_judgement_critical_path_seconds:.2f}s, "
        f"other-research={run.total_unattributed_research_seconds:.2f}s"
    )
    stage_seconds: dict[str, float] = {}
    for case in run.cases:
        for tool_call in case.trace.tool_calls:
            for llm_call in tool_call.research_llm_calls:
                stage_seconds[llm_call.purpose] = (
                    stage_seconds.get(llm_call.purpose, 0.0) + llm_call.seconds
                )
    if stage_seconds:
        print(
            "Research LLM stages: "
            + ", ".join(
                f"{purpose}={seconds:.2f}s" for purpose, seconds in sorted(stage_seconds.items())
            )
        )
    print(f"Tracked cost USD: {run.total_tracked_cost_usd:.6f}")
    if run.error_cases:
        print("Tracked cost is a lower bound because one or more provider calls failed.")
    print(f"Wall time: {run.total_seconds:.2f}s")
    return 0 if run.passed_cases == run.total_cases else 1


if __name__ == "__main__":
    raise SystemExit(main())

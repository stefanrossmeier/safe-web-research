from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from examples.research_agent.live import AgentResearchProfile, build_live_agent
from examples.research_agent.reporting import render_run
from safe_web_research.security import ContentJudgementMode
from safe_web_research.security.openrouter_jev import DEFAULT_JEV_MODEL

_DEFAULT_AGENT_MODEL = "openai/gpt-6-luna"
_DEFAULT_RESEARCH_MODEL = "openai/gpt-6-luna"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a small local tool-using agent whose only web capability is safe-web-research."
        )
    )
    parser.add_argument("task", help="Research task for the outer agent.")
    parser.add_argument(
        "--agent-model",
        default=os.getenv("OPENROUTER_AGENT_MODEL") or _DEFAULT_AGENT_MODEL,
    )
    parser.add_argument(
        "--research-model",
        default=os.getenv("OPENROUTER_MODEL") or _DEFAULT_RESEARCH_MODEL,
    )
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
        "--output",
        type=Path,
        help="Optional JSON trace path. Parent directories are created automatically.",
    )
    parser.add_argument("--json", action="store_true", help="Print the complete JSON trace.")
    args = parser.parse_args()

    brave_api_key = os.getenv("BRAVE_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not brave_api_key or not openrouter_api_key:
        raise SystemExit("BRAVE_API_KEY and OPENROUTER_API_KEY are required")

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
    run = asyncio.run(agent.run(args.task))

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(run.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if args.json:
        print(run.model_dump_json(indent=2))
    else:
        print(render_run(run))
        if args.output is not None:
            print(f"JSON trace: {args.output}")
    return 0 if run.error_type is None else 1


if __name__ == "__main__":
    raise SystemExit(main())

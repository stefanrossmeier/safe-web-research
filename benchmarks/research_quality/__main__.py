from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
from pathlib import Path

from benchmarks.research_quality.models import ResearchQualitySuite
from benchmarks.research_quality.reporting import write_run
from benchmarks.research_quality.runner import run_suite

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CASES = Path(__file__).with_name("cases.json")
_DEFAULT_OUTPUT = _ROOT / "reports" / "research_quality"


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
        description="Run the paid live generic research-quality matrix."
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_TEST_MODEL") or os.getenv("OPENROUTER_MODEL"),
        help="OpenRouter model slug. Defaults to OPENROUTER_TEST_MODEL/OPENROUTER_MODEL.",
    )
    parser.add_argument("--cases", type=Path, default=_DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow development runs from a dirty tree. Do not publish these as authoritative.",
    )
    args = parser.parse_args()

    brave_api_key = os.getenv("BRAVE_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not brave_api_key or not openrouter_api_key:
        raise SystemExit("BRAVE_API_KEY and OPENROUTER_API_KEY are required")
    if not args.model:
        raise SystemExit("Provide --model or configure OPENROUTER_TEST_MODEL/OPENROUTER_MODEL")

    dirty = _git_dirty()
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "Refusing to write research-quality results from a dirty Git tree. "
            "Commit the implementation first or use --allow-dirty for development."
        )

    suite = ResearchQualitySuite.model_validate_json(args.cases.read_text(encoding="utf-8"))
    case_file = str(args.cases.relative_to(_ROOT))
    commit = _git_output("rev-parse", "--short=12", "HEAD")

    print(
        "This benchmark calls real search and LLM providers and may incur API charges.\n"
        f"Model: {args.model}\n"
        f"Cases: {len(suite.cases)}"
    )

    run = asyncio.run(
        run_suite(
            suite,
            brave_api_key=brave_api_key,
            openrouter_api_key=openrouter_api_key,
            model=args.model,
            git_commit=commit,
            git_dirty=dirty,
            case_file=case_file,
        )
    )
    latest_md, latest_json = write_run(run, output_dir=args.output_dir)
    print(f"Wrote {latest_md.relative_to(_ROOT)}")
    print(f"Wrote {latest_json.relative_to(_ROOT)}")
    print(f"Passed {run.passed_cases}/{run.total_cases} cases")
    print(f"Total cost USD: {run.total_cost_usd:.6f}")
    return 0 if run.passed_cases == run.total_cases else 1


if __name__ == "__main__":
    raise SystemExit(main())

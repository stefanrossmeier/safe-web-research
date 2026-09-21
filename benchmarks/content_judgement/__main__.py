from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from benchmarks.content_judgement.models import EvaluationSuite
from benchmarks.content_judgement.reporting import write_run
from benchmarks.content_judgement.runner import run_suite
from safe_web_research.security.openrouter_jev import DEFAULT_JEV_MODEL

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CASES = Path(__file__).with_name("cases.json")
_DEFAULT_OUTPUT = _ROOT / "reports" / "content_judgement"


def _git_state() -> tuple[str | None, bool | None]:
    if shutil.which("git") is None:
        return None, None
    commit = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if commit.returncode != 0 or status.returncode != 0:
        return None, None
    return commit.stdout.strip(), bool(status.stdout.strip())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the live Jev 40-case semantic evaluation.")
    parser.add_argument("--cases", type=Path, default=_DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_JEV_TEST_MODEL", DEFAULT_JEV_MODEL),
    )
    parser.add_argument("--allow-dirty", action="store_true")
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    if not 0.0 <= args.threshold <= 1.0:
        raise SystemExit("--threshold must be between 0 and 1")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be at least 1")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is required")

    suite = EvaluationSuite.from_path(args.cases)
    commit, dirty = _git_state()
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "Refusing to write evaluation artifacts from a dirty Git tree. "
            "Commit changes first or pass --allow-dirty for an exploratory run."
        )

    now = datetime.now(UTC)
    run = await run_suite(
        suite,
        api_key=api_key,
        model=args.model,
        threshold=args.threshold,
        concurrency=args.concurrency,
        timestamp_utc=now.isoformat(),
        git_commit=commit,
        git_dirty=dirty,
        case_file=str(args.cases.relative_to(_ROOT)),
    )
    stem = now.strftime("%Y%m%dT%H%M%SZ")
    md_path, json_path = write_run(run, args.output_dir, stem)
    latest_md, latest_json = write_run(run, args.output_dir, "latest")
    print(f"Wrote {md_path.relative_to(_ROOT)}")
    print(f"Wrote {json_path.relative_to(_ROOT)}")
    print(f"Wrote {latest_md.relative_to(_ROOT)}")
    print(f"Wrote {latest_json.relative_to(_ROOT)}")
    print(
        f"Accuracy={run.summary.accuracy:.1%} precision={run.summary.precision:.1%} "
        f"recall={run.summary.recall:.1%} cost=${run.summary.total_estimated_cost_usd:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))

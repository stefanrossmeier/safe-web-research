from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from benchmarks.security_benchmark.models import BenchmarkSuite
from benchmarks.security_benchmark.reporting import write_run
from benchmarks.security_benchmark.runner import run_suite

_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_CASES = _ROOT / "benchmarks" / "cases" / "security_containment.json"
_DEFAULT_OUTPUT = _ROOT / "benchmarks" / "results"


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
    parser = argparse.ArgumentParser(
        description="Run the deterministic comparative security containment benchmark."
    )
    parser.add_argument("--cases", type=Path, default=_DEFAULT_CASES)
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow benchmark artifacts to be generated from a dirty Git tree.",
    )
    return parser.parse_args()


async def _main() -> int:
    args = _parse_args()
    suite = BenchmarkSuite.from_path(args.cases)
    commit, dirty = _git_state()

    if dirty and not args.allow_dirty:
        raise SystemExit(
            "Refusing to write benchmark results from a dirty Git tree. "
            "Commit changes first or use --allow-dirty for a development run."
        )

    now = datetime.now(UTC)
    run = await run_suite(
        suite,
        timestamp_utc=now.isoformat(),
        git_commit=commit,
        git_dirty=dirty,
        case_file=str(args.cases.relative_to(_ROOT)),
    )
    stem = now.strftime("%Y%m%dT%H%M%SZ")
    markdown_path, json_path = write_run(run, args.output_dir, stem)
    latest_markdown, latest_json = write_run(run, args.output_dir, "latest")

    def display(path: Path) -> str:
        try:
            return str(path.relative_to(_ROOT))
        except ValueError:
            return str(path)

    print(f"Wrote {display(markdown_path)}")
    print(f"Wrote {display(json_path)}")
    print(f"Wrote {display(latest_markdown)}")
    print(f"Wrote {display(latest_json)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))

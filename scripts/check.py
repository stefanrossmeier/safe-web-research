from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence

_REQUIRED_LIVE_ENV = (
    "BRAVE_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENROUTER_TEST_MODEL",
)


def _run(name: str, command: Sequence[str]) -> bool:
    print(f"\n== {name} ==")
    print("$ " + " ".join(command))
    completed = subprocess.run(list(command), check=False)
    return completed.returncode == 0


def _require_live_environment() -> None:
    missing = [name for name in _REQUIRED_LIVE_ENV if not os.getenv(name)]

    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            "Live checks require environment variables: " + joined + ". "
            "Load .env first (for example: set -a; source .env; set +a)."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the repository's standard quality gates. "
            "The default mode is deterministic, network-free, and credential-free."
        )
    )
    parser.add_argument(
        "--include-live",
        action="store_true",
        help=(
            "Also run real Brave/OpenRouter/SafeFetcher integration tests. "
            "This requires credentials, public Internet access, and may incur API cost."
        ),
    )
    args = parser.parse_args()

    python = sys.executable
    gates: list[tuple[str, list[str]]] = [
        (
            "ruff format",
            [python, "-m", "ruff", "format", "--check", "."],
        ),
        (
            "ruff lint",
            [python, "-m", "ruff", "check", "."],
        ),
        (
            "mypy",
            [python, "-m", "mypy", "src"],
        ),
        (
            "deterministic tests",
            [
                python,
                "-m",
                "pytest",
                "-m",
                "not live and not adversarial",
                "-q",
            ],
        ),
        (
            "adversarial tests",
            [python, "-m", "pytest", "-m", "adversarial", "-q"],
        ),
    ]

    if args.include_live:
        _require_live_environment()
        print("\nNOTE: live checks call real external services and may incur provider charges.")
        gates.append(
            (
                "live integration tests",
                [
                    python,
                    "-m",
                    "pytest",
                    "tests/live",
                    "-m",
                    "live",
                    "-q",
                ],
            )
        )

    for name, command in gates:
        if not _run(name, command):
            print(f"\nFAILED: {name}")
            return 1

    print("\nAll requested quality gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

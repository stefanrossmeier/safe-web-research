from __future__ import annotations

import argparse
import os

from safe_web_research.cli import main as cli_main

_REQUIRED_ENV = (
    "BRAVE_API_KEY",
    "OPENROUTER_API_KEY",
)

_DEFAULT_QUESTION = (
    "According to python.org, what is Python 3.15.0rc2 and what does the release page say about it?"
)


def _require_environment() -> None:
    missing = [name for name in _REQUIRED_ENV if not os.getenv(name)]

    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            "Research smoke testing requires environment variables: " + joined + ". "
            "Load .env first (for example: set -a; source .env; set +a)."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one deliberately bounded real CLI research smoke test. "
            "This is separate from the generous generic capability defaults."
        )
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=_DEFAULT_QUESTION,
        help="Research question. Defaults to a narrow python.org release question.",
    )
    parser.add_argument(
        "--domain",
        default="python.org",
        help="Allowed domain for the smoke test (default: python.org).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the complete ResearchResult as JSON.",
    )
    args = parser.parse_args()

    _require_environment()

    cli_args = [
        "research",
        args.question,
        "--domain",
        args.domain,
        "--max-searches",
        "2",
        "--max-fetch-attempts",
        "8",
        "--max-pages",
        "3",
        "--max-bytes-per-page",
        "1000000",
        "--max-total-bytes",
        "2000000",
        "--max-redirects",
        "3",
        "--max-llm-calls",
        "3",
        "--max-input-tokens",
        "80000",
        "--max-output-tokens",
        "12000",
    ]

    if args.json:
        cli_args.append("--json")

    print(
        "This smoke test calls real search and LLM providers and may incur API charges.\n"
        "It intentionally uses a smaller test profile than the generic research defaults."
    )
    print("$ safe-web-research " + " ".join(cli_args))

    return cli_main(cli_args)


if __name__ == "__main__":
    raise SystemExit(main())

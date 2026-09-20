from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True, slots=True)
class SuiteStats:
    name: str
    command: list[str]
    exit_code: int
    tests: int | None = None
    passed: int | None = None
    failures: int | None = None
    errors: int | None = None
    skipped: int | None = None
    seconds: float | None = None


def _run(command: list[str], *, junit_path: Path | None = None) -> SuiteStats:
    completed = subprocess.run(command, check=False)

    if junit_path is None:
        return SuiteStats(
            name=command[-1] if command else "command",
            command=command,
            exit_code=completed.returncode,
        )

    stats = _parse_junit(junit_path)
    return SuiteStats(
        name="",
        command=command,
        exit_code=completed.returncode,
        **stats,
    )


def _parse_junit(path: Path) -> dict[str, int | float]:
    root = ElementTree.parse(path).getroot()

    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

    tests = sum(int(suite.attrib.get("tests", 0)) for suite in suites)
    failures = sum(int(suite.attrib.get("failures", 0)) for suite in suites)
    errors = sum(int(suite.attrib.get("errors", 0)) for suite in suites)
    skipped = sum(int(suite.attrib.get("skipped", 0)) for suite in suites)
    seconds = sum(float(suite.attrib.get("time", 0.0)) for suite in suites)

    return {
        "tests": tests,
        "passed": tests - failures - errors - skipped,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "seconds": round(seconds, 3),
    }


def _public_command(command: list[str]) -> list[str]:
    public = list(command)

    if public and public[0] == sys.executable:
        public = ["uv", "run", "python", *public[1:]]

    return [part for part in public if not part.startswith("--junitxml=")]


def _git_value(*args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    value = completed.stdout.strip()
    return value or None


def _render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# Test run",
        "",
        f"- Timestamp (UTC): `{report['timestamp_utc']}`",
        f"- Git commit: `{report.get('git_commit') or 'unknown'}`",
        f"- Git dirty: `{report['git_dirty']}`",
        f"- Python: `{report['python']}`",
        f"- Platform: `{report['platform']}`",
        f"- OpenRouter live-test model: `{report.get('openrouter_test_model') or 'not recorded'}`",
        "",
        "## Results",
        "",
        "| Gate | Exit | Passed | Failed | Errors | Skipped | Tests | Seconds |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    suites = report["suites"]
    assert isinstance(suites, list)

    for suite in suites:
        assert isinstance(suite, dict)
        failures = suite.get("failures")
        errors = suite.get("errors")
        lines.append(
            "| {name} | {exit_code} | {passed} | {failures} | {errors} | "
            "{skipped} | {tests} | {seconds} |".format(
                name=suite["name"],
                exit_code=suite["exit_code"],
                passed=suite.get("passed", "—") if suite.get("passed") is not None else "—",
                failures=failures if failures is not None else "—",
                errors=errors if errors is not None else "—",
                skipped=suite.get("skipped", "—") if suite.get("skipped") is not None else "—",
                tests=suite.get("tests", "—") if suite.get("tests") is not None else "—",
                seconds=suite.get("seconds", "—") if suite.get("seconds") is not None else "—",
            )
        )

    lines.extend(
        [
            "",
            "## Commands",
            "",
        ]
    )

    for suite in suites:
        assert isinstance(suite, dict)
        command = suite.get("command")
        if isinstance(command, list):
            lines.append(f"- **{suite['name']}**: `{' '.join(str(part) for part in command)}`")

    lines.extend(
        [
            "",
            (
                "> This report records one concrete execution environment. "
                "Live-provider results can vary with external availability, "
                "provider routing, and rate limits."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run quality gates and write reproducible test-run statistics."
    )
    parser.add_argument(
        "--include-live",
        action="store_true",
        help="Also run real external-service tests. Requires credentials.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/test_runs",
        help="Directory for Markdown and JSON reports.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    suites: list[SuiteStats] = []

    suites.append(
        SuiteStats(
            name="ruff-format",
            command=[sys.executable, "-m", "ruff", "format", "--check", "."],
            exit_code=subprocess.run(
                [sys.executable, "-m", "ruff", "format", "--check", "."],
                check=False,
            ).returncode,
        )
    )

    suites.append(
        SuiteStats(
            name="ruff",
            command=[sys.executable, "-m", "ruff", "check", "."],
            exit_code=subprocess.run(
                [sys.executable, "-m", "ruff", "check", "."],
                check=False,
            ).returncode,
        )
    )

    suites.append(
        SuiteStats(
            name="mypy",
            command=[sys.executable, "-m", "mypy", "src"],
            exit_code=subprocess.run(
                [sys.executable, "-m", "mypy", "src"],
                check=False,
            ).returncode,
        )
    )

    with tempfile.TemporaryDirectory(prefix="safe-web-research-tests-") as temp_dir:
        temp = Path(temp_dir)

        deterministic_xml = temp / "deterministic.xml"
        deterministic_command = [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "not live and not adversarial",
            "-q",
            f"--junitxml={deterministic_xml}",
        ]
        deterministic = _run(deterministic_command, junit_path=deterministic_xml)
        suites.append(
            SuiteStats(
                name="deterministic",
                command=deterministic.command,
                exit_code=deterministic.exit_code,
                tests=deterministic.tests,
                passed=deterministic.passed,
                failures=deterministic.failures,
                errors=deterministic.errors,
                skipped=deterministic.skipped,
                seconds=deterministic.seconds,
            )
        )

        adversarial_xml = temp / "adversarial.xml"
        adversarial_command = [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "adversarial",
            "-q",
            f"--junitxml={adversarial_xml}",
        ]
        adversarial = _run(adversarial_command, junit_path=adversarial_xml)
        suites.append(
            SuiteStats(
                name="adversarial",
                command=adversarial.command,
                exit_code=adversarial.exit_code,
                tests=adversarial.tests,
                passed=adversarial.passed,
                failures=adversarial.failures,
                errors=adversarial.errors,
                skipped=adversarial.skipped,
                seconds=adversarial.seconds,
            )
        )

        if args.include_live:
            live_xml = temp / "live.xml"
            live_command = [
                sys.executable,
                "-m",
                "pytest",
                "tests/live",
                "-m",
                "live",
                "-q",
                f"--junitxml={live_xml}",
            ]
            live = _run(live_command, junit_path=live_xml)
            suites.append(
                SuiteStats(
                    name="live",
                    command=live.command,
                    exit_code=live.exit_code,
                    tests=live.tests,
                    passed=live.passed,
                    failures=live.failures,
                    errors=live.errors,
                    skipped=live.skipped,
                    seconds=live.seconds,
                )
            )

    timestamp = datetime.now(UTC)
    stamp = timestamp.strftime("%Y%m%dT%H%M%SZ")
    commit = _git_value("rev-parse", "--short=12", "HEAD")
    dirty = bool(_git_value("status", "--porcelain"))

    report: dict[str, object] = {
        "schema_version": 1,
        "timestamp_utc": timestamp.isoformat(),
        "git_commit": commit,
        "git_dirty": dirty,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "openrouter_test_model": os.getenv("OPENROUTER_TEST_MODEL"),
        "suites": [
            {**asdict(suite), "command": _public_command(suite.command)} for suite in suites
        ],
    }

    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    markdown_text = _render_markdown(report)

    (output_dir / f"{stamp}.json").write_text(json_text)
    (output_dir / f"{stamp}.md").write_text(markdown_text)
    (output_dir / "latest.json").write_text(json_text)
    (output_dir / "latest.md").write_text(markdown_text)

    print(f"Wrote {output_dir / 'latest.md'}")
    print(f"Wrote {output_dir / 'latest.json'}")

    return 0 if all(suite.exit_code == 0 for suite in suites) else 1


if __name__ == "__main__":
    raise SystemExit(main())

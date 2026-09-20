from __future__ import annotations

import json
from pathlib import Path

from benchmarks.security_benchmark.models import BenchmarkRun


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _metric(numerator: int, denominator: int, rate: float) -> str:
    return f"{numerator}/{denominator} ({_percent(rate)})"


def render_markdown(run: BenchmarkRun) -> str:
    lines = [
        "# Comparative security benchmark",
        "",
        f"- Timestamp (UTC): `{run.timestamp_utc}`",
        f"- Git commit: `{run.git_commit or 'unknown'}`",
        f"- Git dirty: `{run.git_dirty}`",
        f"- Case file: `{run.case_file}`",
        "- Live model/API calls: `none`",
        "",
        "## What this benchmark measures",
        "",
        run.methodology,
        "",
        (
            "It intentionally assumes hostile content has already influenced the model. "
            "A lower attack-success rate therefore demonstrates stronger containment of "
            "compromised model behavior, not a claim that prompt injection was detected "
            "or prevented."
        ),
        "",
        "## Aggregate results",
        "",
        (
            "| Architecture | Attack success | Forbidden network executed | "
            "Secret exfiltration accepted | Shell accepted | Invalid provenance accepted | "
            "Action smuggling accepted | Benign completion | Benign warning rate |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for item in run.results:
        metrics = [
            item.architecture,
            _metric(
                item.attack_successes,
                item.adversarial_cases,
                item.attack_success_rate,
            ),
            _metric(
                item.forbidden_network_executed,
                item.forbidden_network_actions,
                item.forbidden_network_execution_rate,
            ),
            _metric(
                item.secret_exfiltration_accepted,
                item.secret_exfiltration_actions,
                item.secret_exfiltration_acceptance_rate,
            ),
            _metric(
                item.shell_actions_accepted,
                item.shell_actions,
                item.shell_action_acceptance_rate,
            ),
            _metric(
                item.invalid_provenance_accepted,
                item.invalid_provenance_actions,
                item.invalid_provenance_acceptance_rate,
            ),
            _metric(
                item.action_smuggling_accepted,
                item.action_smuggling_actions,
                item.action_smuggling_acceptance_rate,
            ),
            _metric(
                item.benign_tasks_completed,
                item.benign_cases,
                item.benign_completion_rate,
            ),
            _metric(
                item.benign_cases_with_security_warnings,
                item.benign_cases,
                item.benign_security_warning_rate,
            ),
        ]
        lines.append("| " + " | ".join(metrics) + " |")

    lines.extend(
        [
            "",
            "## Interpretation constraints",
            "",
            (
                "- The direct-tool baseline is intentionally minimal: proposed actions "
                "are accepted without the bounded-capability controls under test."
            ),
            (
                "- The detector-only baseline uses this repository's heuristic "
                "`SuspiciousContentScanner` as a blocking gate. It is not presented as "
                "representative of every commercial detector."
            ),
            (
                "- The safe-web-research row exercises the real URL policy and the same "
                "provenance allow-list principle used by synthesis, while secret, shell, "
                "arbitrary model-origin URL, and extra-action authority remain unavailable."
            ),
            (
                "- Token usage and provider cost are zero by construction because the "
                "benchmark fixes model behavior instead of sampling a live model. Live "
                "answer quality and cost are separate evaluation concerns."
            ),
            (
                "- Results are evidence for the included case corpus only; they are not "
                "a proof that all future attacks are contained."
            ),
            "",
            "## Per-case outcomes",
            "",
            (
                "| Case | Architecture | Family | Adversarial | Attack succeeded | "
                "Task completed | Scanner findings |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for outcome in run.cases:
        findings = ", ".join(outcome.scanner_findings) or "—"
        lines.append(
            f"| {outcome.case_id} | {outcome.architecture} | {outcome.family} | "
            f"{'yes' if outcome.adversarial else 'no'} | "
            f"{'yes' if outcome.attack_success else 'no'} | "
            f"{'yes' if outcome.task_completed else 'no'} | {findings} |"
        )

    return "\n".join(lines) + "\n"


def write_run(run: BenchmarkRun, output_dir: Path, stem: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    json_path.write_text(
        json.dumps(run.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(run), encoding="utf-8")
    return markdown_path, json_path

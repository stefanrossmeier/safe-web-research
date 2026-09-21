from __future__ import annotations

import json
from pathlib import Path

from benchmarks.content_judgement.models import EvaluationRun


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(run: EvaluationRun) -> str:
    s = run.summary
    lines = [
        "# Jev semantic content-judgement evaluation",
        "",
        f"- Timestamp (UTC): `{run.timestamp_utc}`",
        f"- Git commit: `{run.git_commit or 'unknown'}`",
        f"- Git dirty: `{run.git_dirty}`",
        f"- Configured model: `{run.configured_model}`",
        f"- Case file: `{run.case_file}`",
        f"- Decision threshold used for descriptive metrics: `{s.threshold:.2f}`",
        "",
        "## Methodology",
        "",
        run.methodology,
        "",
        "The benign half is intentionally difficult: it contains quoted attacks, shell and "
        "tool documentation, secret-handling guidance, SSRF examples, fake role markers, and "
        "provenance-attack descriptions. A good result therefore requires context-sensitive "
        "distinction between *describing* an instruction and *issuing* one.",
        "",
        "## Aggregate result",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Cases | {s.cases} ({s.benign_cases} benign / {s.malicious_cases} malicious) |",
        f"| Accuracy at threshold | {_pct(s.accuracy)} |",
        f"| Precision at threshold | {_pct(s.precision)} |",
        f"| Recall at threshold | {_pct(s.recall)} |",
        (
            f"| TP / TN / FP / FN | {s.true_positive} / {s.true_negative} / "
            f"{s.false_positive} / {s.false_negative} |"
        ),
        f"| Benign cases flagged by regex scanner | {s.benign_scanner_warnings}/{s.benign_cases} |",
        (
            f"| Malicious cases flagged by regex scanner | "
            f"{s.malicious_scanner_hits}/{s.malicious_cases} |"
        ),
        f"| Benign mean / max risk | {s.benign_mean_risk:.4f} / {s.benign_max_risk:.4f} |",
        f"| Malicious mean / min risk | {s.malicious_mean_risk:.4f} / {s.malicious_min_risk:.4f} |",
        f"| Total input / output tokens | {s.total_input_tokens} / {s.total_output_tokens} |",
        f"| Total estimated cost USD | ${s.total_estimated_cost_usd:.8f} |",
        f"| Median call duration | {s.median_duration_ms:.1f} ms |",
        "",
        "## Per-case results",
        "",
        (
            "| Case | Expected | Intent | Risk | Override | Capability | Secrets | "
            "Provenance | Regex findings | Result |"
        ),
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in run.cases:
        lines.append(
            f"| {item.case_id} | {item.expected} | `{item.content_intent}` | "
            f"{item.semantic_risk:.4f} | {item.instruction_override_probability:.4f} | "
            f"{item.capability_induction_probability:.4f} | "
            f"{item.secret_exfiltration_probability:.4f} | "
            f"{item.provenance_manipulation_probability:.4f} | "
            f"{', '.join(item.scanner_findings) or '—'} | "
            f"{'PASS' if item.correct_at_threshold else 'MISS'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation constraints",
            "",
            (
                "- This is a live model evaluation, so results may change with "
                "provider/model revisions."
            ),
            "- The threshold is an analysis parameter only. It does not enable evidence filtering.",
            (
                "- Forty authored cases are useful regression/calibration evidence, not a "
                "comprehensive security benchmark."
            ),
            (
                "- The corpus intentionally contains paired semantic contrasts; future versions "
                "should add obfuscation, longer documents, multilingual cases, and naturally "
                "occurring web content."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_run(run: EvaluationRun, output_dir: Path, stem: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(run.model_dump(mode="json"), indent=2, sort_keys=True) + "\n")
    md_path.write_text(render_markdown(run), encoding="utf-8")
    return md_path, json_path

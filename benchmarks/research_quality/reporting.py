from __future__ import annotations

import json
from pathlib import Path

from benchmarks.research_quality.models import ResearchQualityRun


def render_markdown(run: ResearchQualityRun) -> str:
    lines = [
        "# Live research-quality matrix",
        "",
        f"- Timestamp (UTC): `{run.timestamp_utc}`",
        f"- Git commit: `{run.git_commit}`",
        f"- Git dirty: `{run.git_dirty}`",
        f"- Model: `{run.model}`",
        f"- Case file: `{run.case_file}`",
        "",
        "## Aggregate",
        "",
        f"- Passed cases: **{run.passed_cases}/{run.total_cases}**",
        f"- Total input tokens: **{run.total_input_tokens}**",
        f"- Total output tokens: **{run.total_output_tokens}**",
        f"- Total provider cost: **${run.total_cost_usd:.6f}**",
        f"- Total fetch attempts: **{run.total_fetch_attempts}**",
        f"- Total pages fetched: **{run.total_pages_fetched}**",
        f"- Total wall time: **{run.total_seconds:.2f}s**",
        "",
        "## Cases",
        "",
        (
            "| Case | Category | Pass | Terms | Claims verified | Support | "
            "Pages | Input | Output | Cost | Seconds | Hard-limit flags |"
        ),
        "| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for item in run.cases:
        support = (
            f"{item.supported_claims} supported, {item.partial_claims} partial, "
            f"{item.unsupported_claims} unsupported, {item.contradicted_claims} contradicted"
        )
        flags = ", ".join(item.hard_limit_flags) or "—"
        lines.append(
            "| "
            + " | ".join(
                [
                    item.case_id,
                    item.category,
                    "yes" if item.passed else "no",
                    f"{item.expected_terms_found}/{item.expected_terms_total}",
                    f"{item.verified_claims}/{item.claims}",
                    support,
                    str(item.pages_fetched),
                    str(item.input_tokens),
                    str(item.output_tokens),
                    f"${item.estimated_cost_usd:.6f}",
                    f"{item.seconds:.2f}",
                    flags,
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "This is a live provider/network quality matrix, not a security benchmark. "
                "Search results, provider routing, latency, token usage, and cost may vary."
            ),
            (
                "A case passes only when expected anchor terms are present, every synthesized "
                "claim is verified, no claim is unsupported/contradicted, and no hard research "
                "ceiling or synthesis truncation flag is hit. Partial support is allowed."
            ),
            (
                "The expected terms are lightweight regression anchors, not a complete semantic "
                "answer-quality score. Human review remains necessary for publication claims."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_run(
    run: ResearchQualityRun,
    *,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = run.timestamp_utc.replace("-", "").replace(":", "").split(".", 1)[0]
    stamp = stamp.replace("+0000", "").replace("+00", "") + "Z"

    markdown = render_markdown(run)
    json_text = json.dumps(run.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"

    timestamped_md = output_dir / f"{stamp}.md"
    timestamped_json = output_dir / f"{stamp}.json"
    latest_md = output_dir / "latest.md"
    latest_json = output_dir / "latest.json"

    timestamped_md.write_text(markdown, encoding="utf-8")
    timestamped_json.write_text(json_text, encoding="utf-8")
    latest_md.write_text(markdown, encoding="utf-8")
    latest_json.write_text(json_text, encoding="utf-8")

    return latest_md, latest_json

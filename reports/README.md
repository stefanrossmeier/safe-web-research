# Reports

This directory contains **generated evidence artifacts**, not executable benchmark/test logic.

| Directory | Produced by | Meaning |
| --- | --- | --- |
| [test_runs/](test_runs/README.md) | `scripts/record_test_run.py` | quality-gate execution evidence |
| [security_benchmark/](security_benchmark/README.md) | `python -m benchmarks.security` | deterministic containment benchmark evidence |
| [research_quality/](research_quality/README.md) | `python -m benchmarks.research_quality` | live research-quality/efficiency evidence |

For a public release, do not run these independently and commit a mixture of revisions. Use:

```bash
uv run python scripts/record_release_evidence.py \
  --model z-ai/glm-5.3-flash
```

The release-evidence script starts from one clean Git commit, writes all three evaluations to an
ignored staging directory, verifies that they all reference the same clean revision, requires every
quality case to pass and the bounded architecture to retain its containment invariants, and only
then replaces the public report artifacts together.

Timestamped artifacts identify the concrete run; `latest.*` is a convenience copy of that same run.
Older pre-release report artifacts are intentionally not retained in the public tree.

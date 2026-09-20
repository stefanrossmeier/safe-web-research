# Reports

This directory contains **generated evidence artifacts**, not executable benchmark/test logic.

| Directory | Produced by | Meaning |
| --- | --- | --- |
| [test_runs/](test_runs/README.md) | `scripts/record_test_run.py` | quality-gate execution evidence |
| [security_benchmark/](security_benchmark/README.md) | `python -m benchmarks.security` | deterministic containment benchmark evidence |
| [research_quality/](research_quality/README.md) | `python -m benchmarks.research_quality` | live research-quality/efficiency evidence |

Timestamped artifacts identify a specific run; `latest.*` is a convenience copy. Authoritative/public results should be generated from a clean Git revision and reviewed before commit.

Historical artifacts may contain case-file paths that were valid at the commit recorded inside the artifact. Generated evidence is not rewritten after repository-layout changes.

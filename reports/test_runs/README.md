# Recorded Test Runs

Use these artifacts for reproducible quality-gate evidence rather than copied terminal output.

Deterministic/adversarial report:

```bash
uv run python scripts/record_test_run.py
```

Include live provider tests after loading local credentials:

```bash
uv run python scripts/record_test_run.py --include-live
```

Reports include Git commit/dirty state, Python/platform information, portable commands, test counts/results/durations, quality-gate exit codes, and the configured live-test model. Secret values are not recorded.

Timestamped files identify a specific run; `latest.*` is a convenience copy. For release evidence, run from a clean commit.

For public release evidence, prefer `scripts/record_release_evidence.py` so this report is generated
from the same clean commit as the security and research-quality reports.

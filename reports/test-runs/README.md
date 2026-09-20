# Recorded test runs

This directory is for reproducible test-run evidence that can be committed alongside releases or benchmark results.

Generate a deterministic/adversarial report:

```bash
uv run python scripts/record_test_run.py
```

Include real Brave/OpenRouter/SafeFetcher end-to-end tests:

```bash
set -a
source .env
set +a

uv run python scripts/record_test_run.py --include-live
```

The command writes:

- `latest.md` — human-readable summary,
- `latest.json` — machine-readable summary,
- timestamped Markdown/JSON copies for historical runs.

Reports include the git commit, dirty-state flag, Python/platform information, test counts, pass/fail/skip counts, durations, quality-gate exit codes, and the configured live-test model. API keys and other secrets are never recorded.

For release evidence, run from a clean commit and commit the timestamped report together with the release tag or benchmark result.

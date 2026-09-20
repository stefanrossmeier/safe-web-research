# Contributing

Contributions are welcome, especially security regression tests, provider adapters, extraction improvements, and evaluation work.

## Local setup

```bash
uv sync
```

Run the standard gates:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest -m "not live" -q
```

## Security-sensitive changes

Changes involving any of the following should include adversarial tests:

- URL parsing,
- DNS handling,
- redirects,
- IP policy,
- HTTP transports,
- extraction,
- untrusted content handling,
- LLM prompts,
- structured schemas,
- evidence/citation validation,
- provider routing,
- budgets or stopping behavior.

Run:

```bash
uv run pytest -m adversarial -v
```

## Live tests

Live tests require local credentials and may incur provider costs.

Do not place credentials in source, fixtures, test output, or commits.

```bash
set -a
source .env
set +a

uv run pytest tests/live -m live -v
```

## Provider implementations

Provider-specific wire formats should remain inside their adapter.

Core domain models should stay provider-neutral.

Normal deterministic tests must not make real external calls.

## Design expectations

Please preserve these principles:

- models do not own authority,
- untrusted web content is data,
- security decisions are enforced in trusted code,
- failure is preferable to accepting invented provenance,
- resource use is bounded,
- security detectors are defense in depth rather than authorization controls.

## Documentation

If a change alters a trust boundary, security invariant, or deliberate tradeoff, update the relevant architecture/threat-model document and consider adding an ADR.

## Test and benchmark evidence

For release or benchmark work, record a reproducible test-run artifact instead of relying on copied terminal output:

```bash
uv run python scripts/record_test_run.py
```

Use `--include-live` only after loading local credentials. Generated reports under `reports/test-runs/` intentionally contain environment metadata and test statistics but not secret values.

Comparative security claims should follow the methodology in `benchmarks/README.md`. Do not publish a bounded-vs-direct-agent superiority claim without committing the scenario set, model/provider configuration, per-case outcomes, aggregate metrics, and the corresponding test-run report.

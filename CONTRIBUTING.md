# Contributing

Contributions are welcome, especially security regressions, provider adapters, extraction improvements, and evaluation work.

Start with the [Quickstart](docs/QUICKSTART.md) and [Repository Layout](docs/repository-layout.md).

## Local setup

```bash
uv sync
uv run python scripts/check.py
```

The standard gate covers Ruff formatting/linting, mypy, deterministic tests, and the adversarial suite without paid external calls.

## Security-sensitive changes

Changes involving URL/DNS/IP handling, redirects, HTTP transports/decoding, extraction, untrusted content, LLM prompts/schemas, provenance/reference validation, provider routing, budgets/stopping, or new external actions should include adversarial/regression coverage.

Run targeted adversarial tests with:

```bash
uv run pytest -m adversarial -v
```

## Live tests

Live tests require local credentials and may incur provider costs. Do not place credentials in source, fixtures, output, or commits.

```bash
set -a
source .env
set +a

uv run python scripts/check.py --include-live
```

## Provider implementations

Provider-specific wire formats/authentication/error details belong behind provider-neutral interfaces. Core domain/orchestration models should remain provider-neutral.

Normal deterministic tests must not make external calls.

## Design expectations

Preserve these principles:

- models do not own execution authority;
- web content is untrusted data;
- security decisions are enforced in trusted code;
- invented provenance fails closed;
- resource use has hard deterministic ceilings;
- evidence sufficiency is a soft policy below those ceilings;
- heuristic attack detection is observability/defense in depth, not authorization.

## Documentation and ADRs

If a change alters current behavior, update the relevant direct documentation in `docs/`.

If it changes a durable trust-boundary/security/provider/resource tradeoff, add or update an ADR. See [`docs/adr/README.md`](docs/adr/README.md).

Avoid milestone-only language in public docs; describe the capability/decision directly.

## Tests, benchmarks, and reports

- `tests/` contains regression suites and test-only fixtures;
- `benchmarks/` contains evaluation implementations/case definitions;
- `reports/` contains generated evidence artifacts.

See [Testing and Evaluation](docs/testing.md) for exact commands.

Record release-quality evidence with:

```bash
uv run python scripts/record_test_run.py
```

Use `--include-live` only after loading credentials. Generated reports contain execution metadata/statistics, never secret values.

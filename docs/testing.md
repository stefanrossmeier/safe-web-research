# Testing Strategy

The test suite is split by purpose so security-critical logic can be tested without depending on paid APIs or the public Internet.

## Deterministic tests

The standard public quality-gate command is:

```bash
uv run python scripts/check.py
```

It runs formatting validation, Ruff, mypy, deterministic unit/integration/CLI tests, and the adversarial suite as separate non-overlapping gates. It excludes real external services.

For the deterministic pytest subset alone:

```bash
uv run pytest -m "not live and not adversarial" -q
```

Deterministic tests are the primary correctness gate because they are repeatable, credential-free, network-free, fast, and suitable for CI.

## Unit tests

`tests/unit/` covers individual contracts and components, including:

- domain validation,
- Brave response normalization,
- DNS resolution abstractions,
- URL/IP policy,
- SafeFetcher behavior,
- extraction,
- budget accounting,
- OpenRouter payload/response normalization,
- planner/synthesizer validation,
- semantic claim verification,
- suspicious-content scanning,
- CLI parsing/rendering/configuration behavior.

## Integration tests

`tests/integration/` compose fake providers with real orchestration.

They prove properties such as:

- provenance survives search -> fetch -> extraction,
- budgets stop real orchestration paths,
- planner -> gatherer -> synthesizer works without network access,
- synthesized claims cannot invent trusted evidence IDs,
- semantic verification is attached to the correct claims,
- verifier support IDs cannot escape each claim's original citation set,
- unsupported claims are surfaced as quality flags.

## Adversarial tests

Run:

```bash
uv run pytest -m adversarial -v
```

The adversarial suite uses hostile fixtures and deliberately compromised fake-model outputs.

Current cases include:

- prompt injection in fetched HTML,
- hidden instruction-like content,
- fake system/developer messages,
- secret-exfiltration instructions,
- requests to fetch cloud metadata,
- provenance poisoning,
- invented evidence IDs,
- unexpected action fields in model output,
- redirect-based SSRF.

The key assertion is usually not "the model ignored the attack." The stronger assertion is that the attack cannot cross deterministic authority or provenance boundaries.

## Live tests

The standard opt-in live command is:

```bash
set -a
source .env
set +a

uv run python scripts/check.py --include-live
```

This runs the no-cost gates first and then the live-provider suite. To run only the live pytest subset while debugging a provider integration:

```bash
uv run pytest tests/live -m live -v
```

Required variables:

```text
BRAVE_API_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_TEST_MODEL=openai/gpt-5-mini
```

Live tests exercise:

- Brave Search,
- real HTTPS through SafeFetcher address pinning,
- plain OpenRouter completion,
- structured OpenRouter completion,
- full ResearchService end to end, including claim verification.

Live tests use real credentials, may incur cost, depend on external availability, and are intentionally excluded from deterministic CI-style runs.

A live-provider failure should be diagnosed separately from deterministic test failures.

## CLI smoke testing

The CLI itself is deterministically tested with a fake `ResearchService`. A separate opt-in script performs one real, deliberately bounded research request:

```bash
set -a
source .env
set +a

uv run python scripts/research_smoke.py
```

The smoke script uses explicit smaller budgets than the generic capability defaults. This keeps routine end-to-end validation reasonably bounded while leaving the production-facing defaults generous enough for general research. The script calls real providers and may incur API charges.

Use `--json` to inspect the complete public result contract:

```bash
uv run python scripts/research_smoke.py --json
```

Broad research questions using the normal CLI defaults are demos or benchmark workloads, not routine health checks; they can fetch substantially more evidence and therefore use substantially more LLM input tokens.

## Quality gates

Before committing security-sensitive changes, use the standard script:

```bash
uv run python scripts/check.py
```

Before a release, load `.env` and include the live-provider suite:

```bash
set -a
source .env
set +a

uv run python scripts/check.py --include-live
```

Then run the bounded real CLI smoke test separately:

```bash
uv run python scripts/research_smoke.py
```

The live and research-smoke steps are intentionally opt-in because they use external services and may incur cost.

## Adding a security or quality regression test

When a bug is discovered:

1. reproduce it with the narrowest deterministic fixture possible,
2. assert the violated invariant,
3. fix the implementation,
4. retain the regression permanently,
5. update architecture/threat-model documentation if the boundary changed.

Prefer fake providers and fake DNS/HTTP transports. Real external calls should be reserved for `tests/live/`.

## What tests do not prove

Passing tests do not prove:

- perfect prompt-injection resistance,
- factual correctness,
- formal semantic entailment,
- that a verifier verdict is objectively correct,
- absence of all SSRF parser edge cases,
- security of the host/deployment environment,
- security of third-party providers.

The test strategy is designed to make concrete invariants measurable and regressions visible.

## Recording publishable test statistics

For release evidence or portfolio documentation, use the repository test-run recorder rather than copying terminal output by hand:

```bash
uv run python scripts/record_test_run.py
```

To include real external integrations:

```bash
set -a
source .env
set +a

uv run python scripts/record_test_run.py --include-live
```

The recorder writes timestamped and `latest` Markdown/JSON reports under `reports/test-runs/` containing:

- git commit and dirty-state,
- Python/platform information,
- Ruff formatting/linting and mypy exit status,
- deterministic (non-adversarial) test pass/fail/skip counts and duration,
- adversarial test pass/fail/skip counts and duration,
- optional live-test pass/fail/skip counts and duration,
- configured OpenRouter live-test model.

Credentials and secret values are not written to the report.

Release or benchmark claims should link to a committed timestamped report generated from a clean commit.

## Comparative benchmark roadmap

The regression suite answers whether known invariants still hold. It does not by itself answer how much safer the bounded architecture is than a direct-tool agent.

That comparison is specified separately in [`benchmarks/README.md`](../benchmarks/README.md). Planned benchmark dimensions include adversarial attack success, forbidden network actions, provenance integrity, semantic citation support, benign task completion, answer quality, cost, token usage, latency, and false-positive security behavior.

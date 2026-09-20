# Testing Strategy

The test suite is split by purpose so security-critical logic can be tested without depending on paid APIs or the public Internet.

## Deterministic tests

Run:

```bash
uv run pytest -m "not live" -q
```

This includes unit, integration, and adversarial tests while excluding real external services.

Deterministic tests should be the primary correctness gate because they are:

- repeatable,
- credential-free,
- network-free,
- fast,
- suitable for CI.

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
- suspicious-content scanning.

## Integration tests

`tests/integration/` compose fake providers with real orchestration.

They prove properties such as:

- provenance survives search -> fetch -> extraction,
- budgets stop real orchestration paths,
- planner -> gatherer -> synthesizer works end to end without network access,
- usage accounting is preserved.

## Adversarial tests

Run:

```bash
uv run pytest -m adversarial -v
```

Adversarial tests are security regression tests, not general model-safety benchmarks.

Current scenarios cover:

- indirect prompt injection in fetched HTML,
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

Run:

```bash
set -a
source .env
set +a

uv run pytest tests/live -m live -v
```

Required variables:

```text
BRAVE_API_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_TEST_MODEL=openai/gpt-5-mini
```

Live tests currently exercise:

- Brave Search,
- real HTTPS through SafeFetcher address pinning,
- plain OpenRouter completion,
- structured OpenRouter completion,
- full ResearchService end to end.

Live tests:

- use real credentials,
- may incur cost,
- depend on external availability,
- are intentionally excluded from deterministic CI-style runs.

A live-provider failure should be diagnosed separately from deterministic test failures.

## Quality gates

Before committing security-sensitive changes:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest -m "not live" -q
uv run pytest -m adversarial -v
```

Before a release, also run the live suite.

## Adding a security regression test

When a bug is discovered:

1. reproduce it with the narrowest deterministic fixture possible,
2. assert the violated invariant,
3. fix the implementation,
4. retain the regression permanently,
5. add or update the threat-model documentation if the boundary changed.

Prefer fake providers and fake DNS/HTTP transports. Real external calls should be reserved for `tests/live/`.

## What tests do not prove

Passing tests do not prove:

- perfect prompt-injection resistance,
- factual correctness,
- semantic support of every claim by its citations,
- absence of all SSRF parser edge cases,
- security of the host/deployment environment,
- security of third-party providers.

The test strategy is designed to make concrete invariants measurable and regressions visible.

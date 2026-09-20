# Testing and Evaluation

The repository separates **regression tests**, **benchmarks**, and **recorded reports** because they answer different questions.

- `tests/`: does a specific invariant/behavior still pass?
- `benchmarks/`: how does the system behave on a committed evaluation corpus/workload?
- `reports/`: what happened in a concrete run from a specific Git revision?

See [Repository Layout](repository-layout.md) for the directory model.

## Standard no-cost gate

Run:

```bash
uv run python scripts/check.py
```

This executes:

1. Ruff formatting check;
2. Ruff lint;
3. mypy over `src`;
4. deterministic tests excluding live/adversarial markers;
5. adversarial tests as a separate gate.

It does not call Brave/OpenRouter.

## Test suites

### Unit

`tests/unit/` covers individual contracts/components: domain validation, URL/DNS/IP policy, SafeFetcher, gzip handling, extraction, budgets, evidence selection, provider normalization, structured output, planner/synthesizer/verifier behavior, scanner rules, CLI parsing/rendering, and report helpers.

### Integration

`tests/integration/` composes real orchestration with fake external providers. Important properties include provenance preservation, budget behavior, planner→gatherer→synthesizer flow, evidence-reference validation, semantic verification mapping, and quality-flag propagation.

### Adversarial

```bash
uv run pytest -m adversarial -v
```

These tests use hostile fixtures or deliberately compromised fake-model outputs. The key assertion is normally not "the model ignored the attack"; it is that the attack cannot cross deterministic authority/provenance boundaries.

Test-only external-content fixtures live under `tests/fixtures/`.

### Live

Live tests use real external services and may cost money.

With `.env` loaded:

```bash
uv run python scripts/check.py --include-live
```

Or while debugging only live tests:

```bash
uv run pytest tests/live -m live -v
```

Required variables:

```text
BRAVE_API_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_TEST_MODEL=z-ai/glm-5.3-flash
```

The current low-cost test model is GLM 5.3 Flash, but the live suite is intended to expose model/provider compatibility assumptions rather than hard-code that model into the core.

Live coverage includes Brave Search, real SafeFetcher HTTPS, plain/structured OpenRouter calls, and full `ResearchService` behavior including semantic verification.

## Real CLI smoke test

```bash
set -a
source .env
set +a

uv run python scripts/research_smoke.py
```

The smoke script uses deliberately smaller budgets than normal CLI defaults. It is a practical end-to-end health check, not a general research benchmark.

## Deterministic security benchmark

The compromised-model containment benchmark is executable evaluation code under `benchmarks/security/`.

```bash
uv run python -m benchmarks.security
```

It makes no live model/network calls. The same fixed compromised-model proposal is evaluated against:

- bounded `safe-web-research` authority;
- an intentionally minimal direct-tool baseline;
- a detector-only baseline using this repository's heuristic scanner as a gate.

Authoritative runs require a clean Git tree. Development-only dirty runs require:

```bash
uv run python -m benchmarks.security --allow-dirty
```

Generated artifacts go to `reports/security_benchmark/`.

See [security benchmark methodology](../benchmarks/security/README.md).

## Live research-quality benchmark

The live benchmark under `benchmarks/research_quality/` evaluates usefulness/efficiency across unrelated benign tasks using real search, fetching, synthesis, and verification.

```bash
set -a
source .env
set +a

uv run python -m benchmarks.research_quality \
  --model z-ai/glm-5.3-flash
```

It records expected-term coverage, verified claim counts, support verdicts, hard-limit flags, pages/fetches, tokens, provider cost, and wall time.

It is live/stochastic and is **not** a general model ranking. A case passes only when lightweight answer anchors are present, every claim is verified, no claim is unsupported/contradicted, and no hard research ceiling/synthesis truncation is hit. Human review remains necessary.

Generated artifacts go to `reports/research_quality/`.

See [research-quality benchmark methodology](../benchmarks/research_quality/README.md).

## Recorded test-run evidence

For release/portfolio evidence, record the standard gates instead of copying terminal output:

```bash
uv run python scripts/record_test_run.py
```

Include live providers after loading `.env`:

```bash
uv run python scripts/record_test_run.py --include-live
```

Artifacts go to `reports/test_runs/` and include Git revision/dirty state, Python/platform metadata, portable commands, test counts/durations, gate exit codes, and the configured live-test model. Secrets are not recorded.

For publishable evidence, run from a clean committed revision.

## When a bug is found

1. reproduce it with the narrowest deterministic fixture possible;
2. assert the violated invariant;
3. fix the implementation;
4. retain the regression;
5. update direct documentation if current behavior changed;
6. add/update an ADR when the change alters a durable architectural decision/tradeoff.

Prefer fake providers/DNS/transports for regression tests. Reserve real external calls for `tests/live/` and the live benchmark.

## What passing tests do not prove

Passing tests do not prove:

- perfect prompt-injection resistance;
- factual correctness of sources/answers;
- formal semantic entailment;
- verifier infallibility;
- absence of every SSRF/parser edge case;
- security of the host/deployment environment;
- availability/security of third-party providers.

Tests and benchmarks make specific invariants and claims reproducible; they do not turn the project into a formally verified system.

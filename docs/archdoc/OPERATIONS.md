# Operations

> Generated with `ai-craftkit` skill: `archdoc`  
> Source: `https://github.com/stefanrossmeier/safe-web-research` (commit not inspected)  
> Prompt: `inspect this repo and generate the documentation`

Last Reviewed Scope: delta update
Doc Status: DRAFT
Last Operations Update: 2026-09-21 (exact UTC time unavailable)
Updated By: agent
Source Basis: prior full review plus semantic-judgement code/docs/tests/benchmark scan; no commands executed

## Runtime Overview

The project runs as a local CLI or an embedded async Python component. A research request makes outbound calls to Brave Search, public web servers through the bounded fetcher, OpenRouter for planning/synthesis/optional verification, and, by default in the CLI, OpenRouter Decisions for observe-only semantic content judgement. It has no inspected server, worker, scheduler, database, container, or deployment manifest.

## Local Setup

Requirements: Python 3.12+, `uv`, a Brave Search API key, and an OpenRouter API key for real research.

```bash
uv sync
cp .env.example .env
set -a
source .env
set +a
uv run safe-web-research research "What changed in Python 3.15?" --domain python.org
```

Never commit `.env`. The required runtime variables are `BRAVE_API_KEY` and `OPENROUTER_API_KEY`; `OPENROUTER_MODEL` overrides the CLI default. `SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT=off` disables the default observe-only Jev stage and `OPENROUTER_JEV_MODEL` overrides its pinned model. Live tests additionally require `OPENROUTER_TEST_MODEL`; the Jev live test can use `OPENROUTER_JEV_TEST_MODEL`.

## Command Map

| Command | Effect | External cost/network |
|---|---|---|
| `uv run python scripts/check.py` | Ruff format/lint, mypy, deterministic tests, adversarial tests | no |
| `uv run python scripts/check.py --include-live` | Standard gate plus live provider/network tests | yes |
| `uv run python scripts/research_smoke.py` | Smaller-budget real CLI smoke test | yes |
| `uv run python -m benchmarks.security` | Deterministic containment evaluation | no |
| `uv run python -m benchmarks.research_quality --model MODEL` | Live quality/efficiency evaluation | yes |
| `uv run pytest tests/live/test_jev_content_judgement.py -m live -s -vv` | Live check that Jev distinguishes quoted attack discussion from an operative attack | yes |
| `uv run python -m benchmarks.content_judgement --allow-dirty` | Live 40-case Jev evaluation; writes reports under `reports/content_judgement/` | yes |
| `uv run python scripts/record_test_run.py` | Record quality-gate evidence under `reports/test_runs/` | no by default |

## CI

GitHub Actions runs on pushes and pull requests. The `quality` job uses Ubuntu, a ten-minute timeout, `uv sync --locked`, `uv run --frozen python scripts/check.py`, and `uv build`. Live checks remain manual because they require secrets, public network access, and may incur cost.

## Real Request Trace

```text
CLI question
-> argparse builds ResearchRequest from options and environment-based composition
-> ResearchService reserves LLM budget and plans queries
-> EvidenceGatherer calls Brave Search
-> SafeFetcher validates URL/DNS/IP and fetches a bounded public response
-> WebExtractor creates source/evidence; scanner emits optional events
-> EvidenceSelector selects sufficient, diverse evidence or hard budget stops work
-> ContentJudgementObserver samples selected evidence by source and, by default, asks Jev for observe-only risk telemetry
-> ResearchSynthesizer returns answer/claims with evidence references
-> trusted reference validation
-> optional ResearchVerifier returns claim-support verdicts
-> CLI renders text or complete JSON ResearchResult
```

## Failure Modes And First Checks

| Symptom | Likely source | First check |
|---|---|---|
| Exit `2` with missing configuration | Credentials absent | Confirm variable names are loaded, never print values |
| No answer / exit `1` | No gathered evidence or synthesis skipped/failed within budget | Inspect `incomplete_reasons`, security events, and usage in `--json` output |
| Policy violation event | URL/host/port/DNS result disallowed | Inspect `fetch/url_policy.py` and the candidate URL; do not bypass policy casually |
| Fetch error | Timeout, connection, redirect, type/encoding, or byte limit | Inspect emitted event, target behavior, and SafeFetcher tests |
| `content_judgement_error` event | Jev/provider/network/response failure | Evidence remains unchanged; inspect error type and provider status, then use `--content-judgement off` only as an explicit operational opt-out |
| `semantic_content_risk` event | Semantic risk meets the configured threshold | Review source and event metadata; it is telemetry, not evidence removal or a proof of attack |
| Unsupported/contradicted claim | Verifier found weak support | Inspect cited evidence and `ClaimVerification`; do not treat it as a system failure by itself |
| Provider failure | Auth, rate limit, invalid request, or unavailable OpenRouter/Brave | Inspect normalized error and provider status; keep keys out of logs |

## Observability And Evidence

`ResearchResult` is the primary request-level telemetry record. It contains source/evidence provenance, security events, hard-resource usage, judgement call/token/cost fields, provider cost estimate, conflicts, verifier outcomes, and incompleteness reasons. The CLI prints these in human form and `--json` exposes the full structure.

Recorded quality evidence is stored under `reports/test_runs/`, `reports/security_benchmark/`, `reports/research_quality/`, and `reports/content_judgement/`. Timestamped report files preserve particular runs; `latest.*` is a convenience copy. The content-judgement benchmark refuses dirty-tree output unless `--allow-dirty` is supplied.

## Recovery And Safe Operation

- Retry a transient provider or network issue with the same bounded command; inspect the prior result first.
- For an unsafe target or malformed response, retain the policy failure rather than widening fetch permissions as a quick workaround.
- For quality problems, use the narrowest fake-provider/fixture regression before attempting live runs.
- Treat suspicious-content events as signals for review, not as proof of attack or safety.
- Treat semantic-risk events the same way: observe mode is defense-in-depth telemetry and must not be operationally reinterpreted as an authorization boundary.
- Before adding a new consequential capability, update the threat model and ADRs; host-level egress, isolation, secrets, filesystem, and resource controls remain required for sensitive deployments.

## Known Unknowns

- A production deployment target, service supervision model, persistent state store, backup strategy, and health endpoint were not found.
- No commands were executed during this documentation pass, so current test/build health is unverified.
- The package assumes a non-compromised host runtime; deployment controls are documented as external responsibilities rather than implemented operational units.

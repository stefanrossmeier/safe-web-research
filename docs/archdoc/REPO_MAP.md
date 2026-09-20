# Repository Map

> Generated with `ai-craftkit` skill: `archdoc`  
> Source: `https://github.com/stefanrossmeier/safe-web-research` (commit not inspected)  
> Prompt: `inspect this repo and generate the documentation`

Last Reviewed Scope: full review
Doc Status: DRAFT
Last Repo Map Update: 2026-09-20 (exact UTC time unavailable)
Updated By: agent
Source Basis: README/code/docs/tests/CI configuration scan; no commands executed

## Overview

`safe-web-research` is a Python 3.12+ reference implementation for bounded, provenance-aware public-web research. Its main design rule is that models produce structured proposals while trusted Python owns execution authority, network controls, provenance, and resource limits.

## Start Here

1. `README.md` for the product boundary and quick start.
2. `docs/architecture.md` and `docs/threat-model.md` for trust boundaries.
3. `src/safe_web_research/cli.py` for the runnable composition root.
4. `src/safe_web_research/research/service.py` and `gatherer.py` for the orchestration path.
5. `docs/testing.md` and the closest test under `tests/` before changing behavior.

## Directory Map

| Path | Purpose | Status |
|---|---|---|
| `src/safe_web_research/` | Importable product package, domain models, adapters, and orchestration | verified |
| `src/safe_web_research/domain/` | Strict Pydantic request/result, evidence, fetch, search, LLM, security, and budget models | verified |
| `src/safe_web_research/research/` | Planning, gathering, evidence selection, synthesis, verification, stopping, and budgets | verified |
| `src/safe_web_research/fetch/` | URL/DNS policy, resolver, bounded HTTP fetcher, and fakes | verified |
| `src/safe_web_research/search/` | Search protocol, Brave adapter, and fakes | verified |
| `src/safe_web_research/llm/` | LLM protocol, OpenRouter adapter, and fakes | verified |
| `src/safe_web_research/extraction/` | Static HTML/text extraction and fakes | verified |
| `src/safe_web_research/security/` | Suspicious-content scanner used for observability | verified |
| `tests/` | Unit, integration, adversarial, live, benchmark, and fixtures | verified |
| `benchmarks/` | Executable security and live research-quality evaluations | verified |
| `reports/` | Recorded test and benchmark evidence artifacts | verified |
| `scripts/` | Quality gate, smoke, benchmark, and report-recording helpers | verified |
| `docs/` | Public guidance, architecture, threat model, ADRs, and this generated set | verified |

## Entry Points And Commands

| Entry point | Responsibility | Evidence |
|---|---|---|
| `safe-web-research` | Installed console script; calls `safe_web_research:main` | `pyproject.toml`, `src/safe_web_research/__init__.py` |
| `safe-web-research research QUESTION` | Runs one bounded research request | `cli.py` |
| `uv run python scripts/check.py` | Standard credential-free quality gate | `scripts/check.py`, `docs/testing.md` |
| `uv run python scripts/check.py --include-live` | Adds paid/networked live tests after credentials are loaded | `scripts/check.py` |
| `uv run python scripts/research_smoke.py` | Smaller-budget paid end-to-end smoke request | `docs/testing.md` |
| `uv run python -m benchmarks.security` | Deterministic compromised-model containment benchmark | `docs/testing.md` |
| `uv run python -m benchmarks.research_quality --model MODEL` | Live quality/efficiency benchmark | `docs/testing.md` |

## Important Files

| File | Why it matters |
|---|---|
| `src/safe_web_research/cli.py` | CLI arguments, environment lookup, explicit runtime composition, rendering, and exit codes |
| `src/safe_web_research/research/service.py` | Stage sequencing, LLM-budget handling, result/quality flags |
| `src/safe_web_research/research/gatherer.py` | Search/fetch/extract loop, hard-budget consumption, provenance collection, selection, and events |
| `src/safe_web_research/fetch/url_policy.py` | Allowed URL schemes/ports and global-address requirement |
| `src/safe_web_research/fetch/safe.py` | Pinned-address HTTP execution, redirect handling, and bounded body decoding |
| `src/safe_web_research/llm/openrouter.py` | OpenRouter wire adapter and local structured-response validation |
| `docs/threat-model.md` | Security invariants, residual risks, and deployment assumptions |
| `docs/adr/` | Durable rationale for authority, provider, SSRF, injection, verification, and resource decisions |

## Test Map

| Suite | Scope |
|---|---|
| `tests/unit/` | Individual model, policy, fetch, extraction, provider, budget, scanner, and CLI contracts |
| `tests/integration/` | Real orchestration with fake external providers |
| `tests/adversarial/` | Prompt injection, provenance attacks, and SSRF containment |
| `tests/live/` | Brave, OpenRouter, SafeFetcher, and full-service checks requiring credentials/network |
| `tests/benchmark/` | Benchmark implementation tests |

## Conventions

- Keep provider-specific transport/authentication details behind protocols and adapters.
- Preserve the distinction between deterministic authority, provenance integrity, and probabilistic semantic support.
- Use fakes for normal regression tests; do not make deterministic tests call external providers.
- Treat web content and model output as untrusted until validated by trusted code.
- Security-sensitive changes require focused regression/adversarial coverage; durable tradeoff changes require an ADR update.

## High-Risk Areas

| Area | Risk | Inspect first |
|---|---|---|
| URL/DNS/IP, redirects, HTTP transport | SSRF or DNS rebinding | `fetch/url_policy.py`, `fetch/safe.py`, `tests/adversarial/test_ssrf_containment.py` |
| Extraction and untrusted text | Indirect prompt injection affecting quality | `extraction/`, `security/content.py`, `tests/adversarial/test_indirect_prompt_injection.py` |
| Claim/evidence mapping | Fabricated or cross-claim provenance | `research/synthesizer.py`, `research/verifier.py`, provenance tests |
| LLM budgets/stopping | Unbounded cost or incomplete results without a flag | `research/service.py`, `research/llm_budget.py`, `research/budget.py` |
| New tools/actions | Expanding model authority beyond the threat model | `docs/threat-model.md`, `docs/adr/0001-bounded-orchestration.md` |

## Agent Work Guide

Before changing code, identify the owning module, find the nearest existing test, trace the stage in `OPERATIONS.md`, and make the smallest change consistent with the existing authority boundary. Run the narrowest deterministic test first, then `uv run python scripts/check.py` when dependencies are available. Update direct docs for behavior changes and ADRs for durable security/tradeoff changes.

## Known Unknowns

- The exact repository commit and working-tree state were not inspected.
- No test, build, benchmark, or live request was executed during this documentation pass.
- Production deployment, backup, and runtime-hosting configuration were not found in the inspected files.

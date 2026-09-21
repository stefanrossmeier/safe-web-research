# API Surface

> Generated with `ai-craftkit` skill: `archdoc`  
> Source: `https://github.com/stefanrossmeier/safe-web-research` (commit not inspected)  
> Prompt: `inspect this repo and generate the documentation`

Last Reviewed Scope: full review
Doc Status: DRAFT
Last API Surface Update: 2026-09-20 (exact UTC time unavailable)
Updated By: agent
Source Basis: package metadata, CLI, domain models, and quickstart scan; no commands executed

## Scope

There is no HTTP, GraphQL, RPC, webhook, queue, or browser-control API in the inspected code. The supported integration surfaces are a CLI and explicit Python composition API. The package version is `0.1.0`; request/result models use `api_version: "v1"`.

## CLI

Installed command:

```text
safe-web-research research QUESTION [options]
```

| Input | Meaning |
|---|---|
| `QUESTION` | Required research question |
| `--domain DOMAIN` | Repeatable allow-list search-domain restriction |
| `--block-domain DOMAIN` | Repeatable exclusion from search discovery |
| `--freshness-days N` | Restrict discovery to approximately the last N days |
| `--language CODE` / `--country CODE` | Search localization filters |
| `--model SLUG` | OpenRouter model; defaults to `OPENROUTER_MODEL` or `openai/gpt-5-mini` |
| `--content-judgement observe|off` | Jev semantic observability; defaults to `observe`, use `off` to opt out |
| `--jev-model SLUG` | Jev Decisions model; defaults to `OPENROUTER_JEV_MODEL` or `typesafe/jev-1.13` |
| `--no-verify` | Skip semantic claim-support verification |
| `--json` | Emit complete `ResearchResult` as JSON |
| `--max-*` | Override hard ceilings for searches, fetches, pages, bytes, redirects, LLM calls, and tokens |

Required environment variables for real research are `BRAVE_API_KEY` and `OPENROUTER_API_KEY`. `OPENROUTER_MODEL`, `SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT`, and `OPENROUTER_JEV_MODEL` are optional. Semantic content judgement defaults to `observe`; set it to `off` to opt out. Credentials are intentionally not command-line options.

Exit codes: `0` for a synthesized answer, `1` for bounded completion without one, `2` for configuration/validation/research error, and `130` for interruption.

## Python Integration

`ResearchService.research(request: ResearchRequest) -> ResearchResult` is asynchronous. Callers explicitly compose it with:

- `ResearchPlanner` and `ResearchSynthesizer` backed by an `LLMProvider`;
- `EvidenceGatherer` backed by a `SearchProvider`, `Fetcher`, and `Extractor`;
- optional `ResearchVerifier` backed by the same or another `LLMProvider`.

The documented production composition uses `OpenRouterLLMProvider`, `BraveSearchProvider`, `SafeFetcher(URLPolicy(SystemDNSResolver()))`, and `WebExtractor`. The package root exports `main`; domain and research modules expose the models/components required for explicit embedding.

## Main Models

| Model | Contract |
|---|---|
| `ResearchRequest` | Question up to 10,000 characters, hard `ResearchBudget`, optional domain filters/freshness/language/country, `api_version: "v1"` |
| `ResearchPlan` | One to 20 normalized query strings proposed by the planner |
| `EvidenceBundle` | Gathered query list, selected canonical sources/evidence, events, usage, and incompleteness reasons |
| `SynthesisDraft` | Nonempty answer, one to 100 claims, and up to 50 conflicts |
| `ResearchResult` | Answer plus claims, sources/evidence, conflicts, verification outcomes, events, usage, and quality flags |
| `ClaimVerification` | Claim ID, `supported`/`partial`/`unsupported`/`contradicted`, confidence, supporting evidence, and explanation |

Models inherit strict validation, so callers should expect unexpected fields and invalid values to fail rather than be silently accepted.

## Provider Protocols

| Protocol | Method | Implemented adapter |
|---|---|---|
| `LLMProvider` | `complete(LLMRequest) -> LLMResponse` | `OpenRouterLLMProvider` |
| `SearchProvider` | `search(SearchRequest) -> list[SearchResult]` | `BraveSearchProvider` |
| `Fetcher` | `fetch(FetchRequest) -> FetchedDocument` | `SafeFetcher` |
| `Extractor` | extraction of `FetchedDocument` into canonical source/chunks | `WebExtractor` |

The OpenRouter adapter accepts plain or JSON-Schema structured requests, requests strict structured output for schema-bearing calls, and validates returned JSON locally. Provider-specific failures are normalized into typed LLM errors.

## Result And Error Semantics

- A successful process can still return an empty `answer` with explicit `incomplete_reasons` when budgets, evidence, or synthesis prevent an answer.
- Human CLI output includes claims, verifier verdict/confidence, sources, conflicts, security events, quality flags, and usage. `--json` serializes the complete result.
- Security events are telemetry, not a content-safety or authorization verdict.
- Claim references and verifier support references must resolve to trusted context and stay in allowed claim-specific evidence scope.

## Compatibility And Change Rules

- Preserve `api_version: "v1"` semantics when changing request/result models.
- Treat the CLI option/exit-code set and public domain/research exports as integration-relevant.
- Provider adapters may change wire handling internally but must preserve normalized protocol contracts.
- Verify model/schema, CLI, and provenance behavior with the focused unit and integration tests before changing public contracts.

## Smoke Checks

```bash
uv run safe-web-research research "What changed in Python 3.15?" --domain python.org
uv run safe-web-research research "What changed in Python 3.15?" --json
uv run pytest tests/unit/test_cli.py tests/integration/test_research_service.py -q
```

The first two commands require valid provider credentials and public network access; they were not executed for this documentation pass.

## Known Unknowns

- No published HTTP service or versioned remote API contract was found.
- Backward-compatibility policy beyond the current `v1` model fields is not documented.

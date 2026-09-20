# Architecture

## Design rule

`safe-web-research` separates model reasoning from execution authority:

> **Models propose structured data. Trusted Python decides what may execute.**

This is the central design constraint behind network access, provenance, resource budgets, and model integration.

## Data flow

```text
ResearchRequest
      |
      v
ResearchPlanner (LLM, no tools)
      |
      | validated search queries
      v
ResearchService
      |
      v
EvidenceGatherer
      |
      +-- SearchProvider --> Brave Search
      |
      +-- SafeFetcher
      |     +-- URL/DNS/IP policy
      |     +-- validated-address pinning
      |     +-- manual redirect validation
      |     +-- bounded identity/gzip body decoding
      |
      +-- WebExtractor (static HTML/text)
      +-- SuspiciousContentScanner (observability only)
      +-- EvidenceSelector (deterministic relevance/diversity)
      |
      v
EvidenceBundle
      |
      v
ResearchSynthesizer (LLM, no tools)
      |
      | claims + model-facing evidence refs
      v
trusted reference resolution/validation
      |
      v
ResearchVerifier (LLM, no tools)
      |
      | support verdicts + model-facing refs
      v
trusted reference resolution/validation
      |
      v
ResearchResult
      +-- Python API
      +-- CLI
```

The CLI and Python callers use the same `ResearchService`; the CLI is not a separate research implementation.

## Trust boundaries

### Caller input

`ResearchRequest` is untrusted. Pydantic models reject unexpected fields and bound request parameters. Domain filters are validated as domains instead of being passed through as arbitrary search syntax.

### Planner LLM

The planner receives the research question and bounded constraints and may return only a structured `ResearchPlan` containing search queries.

It does not receive search, HTTP, browser, shell, filesystem, or arbitrary action tools. Trusted code validates the plan and enforces the search budget.

### Search provider

`SearchProvider` is provider-neutral. Brave-specific request/response handling stays inside the Brave adapter.

Search results are discovery metadata, not trusted evidence and not a source-quality score. A result URL must still pass the fetch boundary before its contents can become evidence.

### Network fetch boundary

`SafeFetcher` owns HTTP(S) authority. Current policy includes:

- HTTP and HTTPS only;
- ports 80 and 443 only;
- no URL user information;
- no single-label/internal-style hostnames;
- DNS resolution before connection;
- every resolved address must be globally reachable;
- mixed public/private answers are rejected;
- automatic redirects are disabled;
- every redirect target is fully revalidated;
- the connection uses an address that trusted code already validated;
- the original hostname is preserved for HTTP `Host` and TLS SNI;
- environment proxies are ignored;
- keep-alive is disabled for this bounded fetch path;
- allowed content types are restricted;
- response bodies are bounded.

The validated-address binding matters: validating one DNS lookup and then letting an HTTP client independently resolve the hostname again would reopen a DNS-rebinding/TOCTOU gap.

See [ADR 0003](adr/0003-ssrf-target-validation.md).

### HTTP content decoding

The fetcher advertises `gzip, identity` and consumes the raw response stream itself.

For gzip responses it bounds both the compressed stream and the decompressed output. The per-page byte limit is applied to decompressed content before extraction. Malformed, truncated, concatenated, and unsupported encodings fail closed.

This avoids relying on transparent client decompression whose resource accounting could differ from the project's own limits.

See [ADR 0007](adr/0007-bounded-http-content-decoding.md).

### Extraction

`WebExtractor` statically parses HTML/plain text and does not execute JavaScript.

Scripts, styles, templates, SVG, canvas, iframes, navigation, footers, asides, and forms are removed from HTML extraction. Static extraction can still include misleading or visually hidden text; all extracted text therefore remains untrusted data.

### Suspicious-content scanner

`SuspiciousContentScanner` flags a small set of explicit attack-like patterns such as role impersonation, instruction overrides, secret-exfiltration requests, network retargeting, tool-use instructions, and provenance manipulation.

A scanner finding becomes a security event. It does **not** remove evidence, authorize anything, or establish that unflagged text is safe. The benchmark intentionally includes attacks the scanner misses and benign text it flags.

See [ADR 0004](adr/0004-indirect-prompt-injection-containment.md).

### Evidence gathering and selection

`EvidenceGatherer` is trusted orchestration code. It owns:

- search issuance;
- URL deduplication;
- fetch-attempt and successful-page accounting;
- extraction;
- content-hash deduplication;
- source/evidence provenance;
- security/fetch/provider events;
- hard budget enforcement;
- deterministic evidence selection and early stopping.

Hard budgets are safety circuit breakers. They are deliberately separate from normal research shape.

`EvidenceSelector` provides the soft layer. It scores chunks from question/planner terms, preserves source diversity, limits per-source dominance, bounds selected evidence, and declares a set sufficient only when configured diversity, relevance, text-volume, and question-term coverage thresholds are met.

The current default soft policy is:

- at least 2 selected sources;
- at least 4 relevant chunks;
- at least 16,000 selected characters;
- at least 50% question-term coverage;
- no more than 8 selected chunks per source;
- no more than 200,000 selected characters.

This is a heuristic stopping policy, not a semantic completeness claim. If evidence is weak, research may continue toward the hard ceilings.

See [ADR 0006](adr/0006-resource-budgets-and-evidence-sufficiency.md).

### Synthesizer LLM

The synthesizer receives the question plus selected evidence. Evidence is explicitly framed as untrusted data, but security does not rely on the prompt alone: the synthesizer has no tools or network authority.

The model returns a strict `SynthesisDraft`. Evidence is exposed through short model-facing references such as `E1`; trusted code maps those back to canonical evidence IDs and rejects invented references.

The synthesizer cannot create trusted `Source` or `EvidenceChunk` objects.

### Semantic claim verifier

Reference integrity answers "did this claim cite evidence that exists?" It does not answer "does that evidence actually support the claim?"

`ResearchVerifier` therefore performs a separate structured model call. It receives each claim and only the evidence already cited by that claim. Model-facing identifiers (`Q1`, `E1`, ...) are dynamically constrained by the response schema and are resolved back to canonical IDs by trusted code.

Trusted validation requires:

- every synthesized claim is verified exactly once;
- no unknown/duplicate claim reference is accepted;
- supporting evidence stays inside the claim's original citation set;
- supported/partial verdicts identify at least one supporting evidence item.

Verdicts are `supported`, `partial`, `unsupported`, or `contradicted`. This is probabilistic quality control, not formal entailment or independent fact checking.

See [ADR 0005](adr/0005-semantic-claim-verification.md).

### LLM provider boundary

`LLMProvider` keeps provider-specific wire details out of the research core. The included OpenRouter adapter supports plain and JSON-Schema structured requests, normalizes usage/cost metadata, surfaces provider failures, and locally validates structured responses after the provider returns them.

The model is configurable. Core logic must not depend on a particular model reproducing application-internal identifiers; trusted code owns canonical identity and mapping.

See [ADR 0002](adr/0002-provider-abstractions.md).

## Resource budgets

`ResearchBudget` is a hard per-request ceiling. Current defaults are intentionally generous circuit breakers:

| Resource | Default |
| --- | ---: |
| search requests | 10 |
| fetch attempts | 40 |
| successful pages | 20 |
| bytes per page | 5,000,000 |
| total fetched bytes | 50,000,000 |
| redirects per fetch | 5 |
| LLM calls | 10 |
| cumulative input tokens | 500,000 |
| cumulative output tokens | 50,000 |

Fetch attempts and successful pages are separate so blocked/failed responses do not consume the successful-page budget.

Input-token usage is accounted from provider responses, so exact pre-enforcement is limited without a provider/model-specific tokenizer. The system therefore uses trusted cumulative accounting plus bounded per-call behavior and explicit incompleteness/quality flags.

## Authority, provenance, and quality are different questions

The architecture keeps three concerns separate:

1. **Authority:** can hostile content cause a forbidden action? Deterministic capability boundaries answer this.
2. **Provenance:** does a returned citation refer to evidence actually collected and supplied? Trusted reference validation answers this.
3. **Support:** does cited evidence semantically support the claim? The verifier improves this signal, probabilistically.

Collapsing these concerns into one "is this content safe?" classifier would make the security boundary depend on model/detector accuracy.

## Deployment boundary

The package assumes the host Python runtime is not already compromised. Sensitive deployments should add independent controls such as restricted egress, process/container isolation, secret management, filesystem restrictions, and resource limits.

Those deployment controls complement the application design; they are not implemented by this package.

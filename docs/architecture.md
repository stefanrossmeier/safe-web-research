# Architecture

## Overview

`safe-web-research` is a protocol-neutral research core built around one design rule:

> Trusted Python code owns authority; models propose structured data.

Planning, search, fetching, extraction, evidence handling, synthesis, semantic verification, and presentation are separated so each trust boundary can be tested independently.

## Data flow

```text
ResearchRequest
      |
      v
ResearchPlanner
  LLMProvider
      |
      | validated ResearchPlan
      v
ResearchService
      |
      v
EvidenceGatherer
      |
      +---- SearchProvider ----> Brave Search
      |
      +---- SafeFetcher
      |       |
      |       +---- URLPolicy
      |       +---- DNSResolver
      |       +---- validated IP connection
      |       +---- manual redirects
      |
      +---- Extractor ----> WebExtractor
      |
      +---- SuspiciousContentScanner
      |
      v
EvidenceBundle
      |
      v
ResearchSynthesizer
  LLMProvider
      |
      | validated SynthesisDraft
      v
trusted evidence-reference validation
      |
      v
ResearchVerifier
  LLMProvider
      |
      | claim + cited evidence only
      | validated VerificationDraft
      v
trusted verification-reference validation
      |
      v
ResearchResult
      |
      +---- Python API
      |
      +---- CLI
```

## Trust boundaries

### Caller input

`ResearchRequest` is untrusted. Pydantic models reject extra fields and enforce bounded values. Domain filters are validated as domain names rather than accepted as arbitrary search syntax.

### Search provider

Search providers return normalized `SearchResult` objects. Search rank is discovery metadata, not a trust score.

Search results do not directly become evidence. Their URLs must pass the fetch layer.

### Network fetch boundary

`SafeFetcher` is the primary network authority.

V1 policy:

- only HTTP and HTTPS,
- only ports 80 and 443,
- no URL userinfo,
- no single-label/internal-style hostnames,
- all resolved addresses must be globally reachable,
- automatic redirects are disabled,
- each redirect target is fully revalidated,
- the HTTP connection uses an already-validated address,
- the original hostname is preserved for `Host` and TLS SNI,
- environment proxies are ignored,
- keep-alive is disabled,
- response size is bounded,
- accepted MIME types are restricted,
- compressed responses are rejected.

This prevents the common unsafe design where code validates one DNS lookup and the HTTP library performs another lookup during connection.

### Extraction boundary

`WebExtractor` statically parses HTML or plain text. It does not execute JavaScript.

Scripts, styles, templates, SVG, canvas, iframes, navigation, footers, asides, and forms are removed from HTML extraction.

Static parsing can still include content that a browser might visually hide with CSS. That content remains untrusted data and is handled by the same downstream containment rules.

### Suspicious-content scanner

`SuspiciousContentScanner` detects a small set of explicit prompt-injection-like patterns, including role impersonation, instruction override attempts, secret-exfiltration requests, internal-network retargeting, tool-use instructions, and provenance manipulation.

It produces `SUSPICIOUS_CONTENT` security events.

It does **not** remove evidence and does **not** make authorization decisions. It is deliberately a monitoring layer because heuristic detection is incomplete and bypassable.

### Planner LLM

The planner sees the caller's question and bounded research constraints. It returns only a `ResearchPlan` containing search queries.

The planner does not receive search, fetch, shell, filesystem, or browser tools.

Trusted code validates the returned plan and applies search budgets.

### Evidence gatherer

`EvidenceGatherer` is trusted orchestration code. It:

- limits searches,
- limits fetch attempts independently from successful pages,
- limits successfully fetched pages,
- limits bytes,
- deduplicates URLs and content,
- records provider/fetch/extraction/security events,
- preserves source/evidence provenance,
- stops when budgets or configured stopping conditions are reached.

### Synthesizer LLM

The synthesizer receives the user's question plus serialized evidence.

Its system instruction explicitly treats evidence as untrusted data. More importantly, the model has no tools or network authority.

The model returns a strict `SynthesisDraft`, not `Source` or `EvidenceChunk` objects.

Trusted code verifies:

- claim IDs are unique,
- claim evidence IDs refer only to evidence included in the synthesis context,
- conflict IDs are unique,
- conflict claim IDs refer to actual generated claims.

Invented evidence references fail closed.

### Semantic claim verifier

Reference validation answers "does this evidence ID exist?" but not "does this evidence support this claim?"

When configured, `ResearchVerifier` performs a separate structured LLM call after synthesis. For each synthesized claim it receives only:

- the claim ID and text,
- evidence chunks already cited by that claim,
- provenance metadata for those chunks.

The verifier returns `supported`, `partial`, `unsupported`, or `contradicted` plus a confidence value and the subset of cited evidence it believes provides support.

Trusted code then enforces:

- every claim is verified exactly once,
- no unknown claim IDs,
- no evidence IDs outside the claim's existing citations,
- supported/partial verdicts identify at least one supporting evidence item.

The verifier cannot add authority, sources, URLs, tools, or network actions. It is a quality-control layer, not a security authorization layer and not a formal proof system.

### LLM provider boundary

OpenRouter is behind `LLMProvider`.

Structured output requests use JSON Schema at the provider and are validated again locally. The provider response model ignores unrelated provider-specific response fields but rejects missing required normalized fields.

### Resource budgets

`ResearchBudget` controls:

- search count,
- fetch/page attempts,
- bytes per page,
- total bytes,
- redirects,
- LLM calls,
- input tokens,
- output tokens.

Trusted trackers account for usage. A full planner + synthesis + verification run normally requires three LLM calls. If budgets are smaller, the service degrades explicitly and records incomplete/quality reasons rather than silently exceeding them.

## Authority versus quality

The architecture separates three questions:

1. **Can hostile content gain authority?**
2. **Does a citation reference real collected evidence?**
3. **Does that evidence semantically support the claim?**

The first is addressed with deterministic capability boundaries.

The second is addressed with trusted provenance/reference validation.

The third is improved with a separate semantic verification pass, but remains probabilistic and does not establish real-world truth.

## Adapters

The Python API and CLI both call the same `ResearchService`.

The CLI is intentionally thin: it does not perform its own search/fetch logic and therefore does not create a second authority path.

Future REST or MCP adapters must preserve the same property.

## Deployment

Application-level controls should be complemented by deployment controls in production, such as:

- restricted egress,
- non-root containers,
- read-only filesystems where possible,
- no host Docker socket,
- no unnecessary mounts,
- resource limits,
- secret injection through deployment mechanisms rather than files.

Deployment hardening is outside the current Python-core milestone.

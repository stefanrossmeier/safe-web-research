# Architecture

## Overview

`safe-web-research` is a protocol-neutral research core built around a single design rule:

> Trusted Python code owns authority; models propose structured data.

The implementation deliberately separates planning, search, fetching, extraction, evidence handling, model inference, and synthesis so each boundary can be tested independently.

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
reference validation
      |
      v
ResearchResult
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

This prevents the common unsafe design where code validates one DNS lookup and the HTTP library performs a different lookup during connection.

### Extraction boundary

`WebExtractor` statically parses HTML or plain text. It does not execute JavaScript.

Scripts, styles, templates, SVG, canvas, iframes, navigation, footers, asides, and forms are removed from HTML extraction.

Static parsing can still include content that a browser might visually hide with CSS. That content remains untrusted data and is handled by the same downstream containment rules.

### Suspicious-content scanner

`SuspiciousContentScanner` detects a small set of explicit prompt-injection-like patterns, including role impersonation, instruction override attempts, secret-exfiltration requests, internal-network retargeting, tool-use instructions, and provenance manipulation.

It produces `SUSPICIOUS_CONTENT` security events.

It does **not** remove evidence and does **not** make authorization decisions. It is deliberately a monitoring layer, because heuristic detection is incomplete and bypassable.

### Planner LLM

The planner sees the caller's question and bounded research constraints. It returns only a `ResearchPlan` containing search queries.

The planner does not receive search, fetch, shell, filesystem, or browser tools.

Trusted code validates the returned plan and applies search budgets.

### Evidence gatherer

`EvidenceGatherer` is trusted orchestration code. It:

- limits searches,
- limits fetch attempts,
- limits bytes,
- deduplicates URLs and content,
- records provider/fetch/extraction/security events,
- preserves source/evidence provenance,
- stops when budgets or configured stopping conditions are reached.

### Synthesizer LLM

The synthesizer receives the user's question plus serialized evidence.

Its system instruction explicitly treats evidence as untrusted data. More importantly, the model has no tools or network authority.

The model returns a strict `SynthesisDraft`, not `Source` or `EvidenceChunk` objects.

Trusted code then verifies:

- claim IDs are unique,
- claim evidence IDs refer only to evidence included in the synthesis context,
- conflict IDs are unique,
- conflict claim IDs refer to actual generated claims.

Invented evidence references fail closed.

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

Trusted trackers account for usage. If only one LLM call is available, the service skips LLM planning and reserves the call for synthesis.

## Authority versus quality

The architecture separates two questions:

1. **Can hostile content gain authority?**
2. **Can hostile or false content influence the answer?**

The first is addressed with deterministic capability boundaries.

The second cannot be solved purely by sandboxing. Source quality, misinformation, semantic citation support, and conflicting evidence require further evaluation and verification.

## Protocol adapters

The core implementation currently targets the Python API.

Future adapters may expose the same `ResearchService` through CLI, REST, or MCP. Those adapters must not bypass core budgets or fetch policy.

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

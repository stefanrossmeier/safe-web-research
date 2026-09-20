# Threat Model

## Status

M10 threat model for the pre-1.0 standalone research core.

This document describes security properties implemented and tested in the current codebase. It is not a claim of formal verification or production certification.

## Security objective

All Internet-derived content is untrusted.

Security must not depend on the LLM correctly recognizing or resisting prompt injection.

The primary invariant is:

> If an attacker completely succeeds in manipulating the research LLM, they may influence research quality or correctness, but they must not thereby obtain secrets, internal network access, arbitrary network destinations, filesystem mutation, shell execution, or consequential external actions.

## Assets

- Brave credentials
- OpenRouter credentials
- caller-provided data
- host and internal network
- cloud metadata endpoints
- local filesystem
- research integrity
- source/evidence provenance
- cost and resource budgets

## Untrusted inputs

- research questions
- model-generated search queries
- search results and snippets
- URLs
- DNS answers
- redirect targets
- HTTP headers
- HTML and plain text
- extracted evidence
- LLM outputs
- provider error payloads

## V1 non-goals

V1 does not provide:

- browser automation,
- JavaScript execution,
- website authentication,
- arbitrary page interaction,
- file downloads outside bounded text fetching,
- shell access,
- filesystem mutation,
- email or messaging actions,
- persistent memory,
- arbitrary external tools,
- high-impact autonomous actions.

## Threats and controls

### Indirect prompt injection

**Scenario:** A fetched page contains instructions such as fake system/developer messages, requests to ignore previous instructions, secret-exfiltration commands, or tool-use directions.

**Primary controls:**

- the synthesizer has no tools,
- evidence is serialized as data,
- trusted orchestration owns all network actions,
- synthesis output is constrained to a strict schema,
- invented evidence IDs are rejected.

**Defense in depth:**

- static HTML extraction removes script/style and several non-content elements,
- a heuristic scanner records explicit suspicious patterns,
- adversarial fixtures exercise hidden-text and instruction-like content.

**Residual risk:** An injected page can still influence the natural-language model and therefore research quality. The scanner is incomplete and must not be treated as an authorization control.

### Tool abuse / excessive agency

**Scenario:** Hostile evidence instructs the model to browse another URL, execute a command, or use a tool.

**Controls:**

- planner and synthesizer receive no tools,
- `SynthesisDraft` has no action fields,
- strict Pydantic models reject extra output fields,
- network calls occur only through trusted gatherer/fetcher code.

### SSRF and cloud metadata access

**Scenario:** A search result or redirect attempts to reach loopback, RFC1918/private space, link-local addresses, CGNAT, IPv6 local addresses, or cloud metadata.

**Controls:**

- URL scheme/port restrictions,
- DNS resolution before connection,
- all resolved addresses must be global,
- mixed public/private DNS answers are rejected,
- connection is pinned to validated addresses,
- redirects are manual and fully revalidated,
- automatic environment proxies are disabled.

### DNS rebinding / TOCTOU

**Scenario:** A hostname resolves to a public address during validation and a private address when the HTTP library connects.

**Controls:**

- trusted code resolves and validates addresses,
- the HTTP request connects to the validated address rather than asking the client to resolve the hostname again,
- original hostname is preserved for HTTP `Host` and TLS SNI.

### Secret exfiltration

**Scenario:** External content asks the model to reveal credentials or encode them into another request.

**Controls:**

- credentials are held by provider adapters, not evidence,
- synthesizer has no network or tool authority,
- fetch requests contain no LLM/provider credentials,
- `.env` is local-only,
- suspicious explicit exfiltration text is observable.

**Residual risk:** Caller questions and evidence are sent to the configured LLM provider. Do not place secrets into research questions or source content if provider disclosure is unacceptable.

### Citation / provenance poisoning

**Scenario:** Hostile content tells the model to invent evidence IDs or cite attacker-controlled provenance.

**Controls:**

- `Source` and `EvidenceChunk` objects are created by trusted code,
- synthesizer output can reference IDs but cannot create trusted evidence,
- every returned evidence ID is checked against the exact evidence set sent to synthesis,
- unknown evidence IDs fail closed,
- extra action/provenance output fields fail schema validation.

**Residual risk:** An existing evidence chunk may be cited even when it does not semantically support the claim. Semantic entailment verification is a separate quality/security milestone.

### Resource exhaustion / denial of wallet

**Scenario:** Queries, redirects, pages, large bodies, or repeated model calls exhaust compute or API budgets.

**Controls:**

- maximum searches,
- maximum page/fetch attempts,
- per-page and total byte caps,
- redirect caps,
- model-call caps,
- output-token caps,
- tracked input-token usage,
- stopping after repeated no-evidence queries.

**Residual risk:** Provider-side token accounting is reported after a call, so an input-token budget cannot be perfectly pre-enforced without a model-specific tokenizer.

### Malformed or adversarial provider responses

**Scenario:** Search or LLM providers return unexpected fields, invalid JSON, malformed structured output, or unsupported data.

**Controls:**

- provider-specific wire models,
- normalized internal models,
- Pydantic strict models,
- JSON Schema validation for structured LLM output,
- typed provider errors.

### Misinformation and source manipulation

**Scenario:** Search results or fetched sources are false, stale, SEO-manipulated, duplicated, or mutually inconsistent.

**Controls currently present:**

- provenance preservation,
- content-hash deduplication,
- conflict representation,
- domain allow/block filters,
- freshness controls.

**Residual risk:** Search rank is not source trust. V1 does not yet implement authoritative-source scoring or semantic claim verification.

## Security-event semantics

`SecurityEvent` records conditions observed during research.

A `SUSPICIOUS_CONTENT` event means a heuristic rule matched external content. It does not mean an attack was proven, and absence of the event does not mean content is safe.

Security events are intended for observability, evaluation, and later policy layers.

## Adversarial regression suite

Current adversarial scenarios include:

- indirect prompt injection embedded in HTML,
- fake system/developer messages,
- hidden CSS content,
- requests to fetch cloud metadata,
- requests to disclose API keys,
- provenance/citation manipulation,
- a simulated compromised model inventing evidence IDs,
- a simulated compromised model emitting an action field,
- redirect-based SSRF to link-local metadata addresses.

Run:

```bash
uv run pytest -m adversarial -v
```

## Deployment assumptions

The Python implementation assumes the host runtime itself is not compromised.

For sensitive deployments, pair application controls with independent network egress controls, process/container isolation, secret management, resource limits, and monitoring.

## References

The design is informed by OWASP guidance on:

- LLM prompt injection prevention,
- AI agent security and least privilege,
- SSRF prevention,
- structured adversarial testing.

The architecture intentionally treats model-based detection as defense in depth rather than the primary authorization boundary.

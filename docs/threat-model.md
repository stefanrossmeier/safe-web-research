# Threat Model

## Status

This threat model describes the current pre-1.0 standalone research core and CLI. It documents implemented/tested properties; it is not a formal verification or independent security audit.

## Security objective

All Internet-derived content is untrusted. Security must not require the LLM to recognize or resist prompt injection correctly.

Primary invariant:

> If hostile content completely succeeds in influencing a research model, that influence may degrade answer quality, but it must not thereby grant secrets, internal-network access, arbitrary network destinations, filesystem mutation, shell execution, fabricated trusted provenance, or consequential external actions.

## Assets

- Brave and OpenRouter credentials;
- caller-provided data;
- host/internal network and cloud metadata endpoints;
- local filesystem/runtime;
- research integrity;
- source/evidence provenance;
- network, token, and provider-cost budgets.

## Untrusted inputs

- research questions;
- model-generated search queries;
- search results/snippets;
- URLs, DNS answers, redirects, HTTP headers/bodies;
- HTML/plain text and extracted evidence;
- LLM outputs;
- provider error payloads.

## Current non-goals

The project does not provide:

- browser automation or JavaScript execution;
- authenticated website interaction;
- arbitrary file downloads outside bounded text fetching;
- shell or filesystem mutation;
- email/messaging/consequential external actions;
- persistent memory;
- arbitrary external tools;
- protection from a compromised host/Python runtime.

Adding any of those capabilities would require a new threat-model/ADR review rather than being treated as an ordinary adapter change.

## Threats and controls

### Indirect prompt injection

**Scenario:** fetched content contains fake system/developer messages, instruction overrides, secret requests, tool commands, or policy claims aimed at the model.

**Primary controls:**

- planner/synthesizer/verifier have no arbitrary tools;
- external actions remain in trusted orchestration;
- model output is schema constrained and locally validated;
- canonical claim/evidence identity remains in trusted code;
- unexpected action/provenance fields fail validation.

**Defense in depth:** static extraction removes common non-content elements, the heuristic scanner emits suspicious-content events, and default-on Jev observe mode emits independent semantic risk telemetry over selected evidence in the reference application.

**Residual risk:** hostile evidence can still influence wording, source choice, and factual quality. Scanner/Jev misses do not weaken the authority boundary, and false positives do not remove evidence in observe mode.

### Tool abuse / excessive agency

**Scenario:** hostile text tells a model to fetch another URL, execute a command, read a file, or perform a new action.

**Controls:** those capabilities are not available to the research models. Network calls occur through the trusted search/fetch path only.

### SSRF and cloud metadata access

**Scenario:** search results or redirects target loopback/private/link-local/shared/reserved destinations or cloud metadata.

**Controls:** scheme/port policy, hostname validation, pre-connection DNS resolution, all-address globality requirement, rejection of mixed DNS answers, validated-address pinning, manual redirect validation, and `trust_env=False`.

### DNS rebinding / validation-to-connection TOCTOU

**Scenario:** a hostname resolves publicly during validation but privately when the HTTP client connects.

**Control:** the request connects to an already-validated address while preserving the logical hostname for `Host` and TLS SNI.

### Compressed-content resource amplification

**Scenario:** a small compressed response expands beyond the intended page/resource budget or contains malformed/ambiguous gzip streams.

**Controls:** raw gzip is decoded incrementally by trusted code; compressed and decompressed bytes are bounded; the page limit applies to decompressed content; truncated/concatenated/malformed gzip and unsupported encodings fail closed.

### Secret exfiltration

**Scenario:** external content asks the model to disclose provider credentials or encode them into a request.

**Controls:** credentials stay inside provider adapters; research models have no generic network/action tool; fetch requests do not carry LLM/search credentials; `.env` is local-only.

**Residual risk:** the caller's question and selected evidence are sent to the configured LLM provider. Do not submit secrets if provider disclosure is unacceptable.

### Citation/provenance poisoning

**Scenario:** hostile content asks a model to invent evidence/source IDs or cite attacker-selected provenance.

**Controls:** trusted code creates `Source`/`EvidenceChunk`; models only return short references; verifier output is keyed by the supplied claim references and each claim has a claim-specific evidence enum; references are resolved against the exact trusted context; unknown references, cross-claim evidence, and extra fields fail closed.

### Unsupported claims with valid citations

**Scenario:** a claim cites real evidence but overstates, combines, or contradicts it.

**Control:** the optional/default verifier checks each claim against only its already-cited evidence and surfaces `supported`, `partial`, `unsupported`, or `contradicted`.

**Residual risk:** semantic verification is probabilistic and sources themselves may be false. A `supported` verdict does not establish objective truth.

### Resource exhaustion / denial of wallet

**Scenario:** excessive searches, fetches, redirects, large bodies, decompression, evidence accumulation, or model calls consume resources/cost.

**Controls:** hard limits on searches, fetch attempts, successful pages, per-page/total bytes, redirects, LLM calls, input/output tokens; deterministic evidence selection/early stopping; repeated-no-evidence stopping.

**Residual risk:** provider input-token usage is known precisely only after a call without model-specific local tokenization.

### Malformed/adversarial provider responses

**Scenario:** a provider returns invalid JSON, unexpected fields, truncated structured output, unsupported parameters, malformed data, or incorrect semantic-risk probabilities.

**Controls:** provider-specific wire handling, normalized internal models, JSON Schema for structured output, local Pydantic validation, typed provider errors, trusted identifier resolution, and isolation of Jev behind a separate `ContentSecurityJudge` adapter. Jev output remains observability data rather than authorization.

### Misinformation / source manipulation

**Scenario:** sources are false, stale, SEO-manipulated, duplicated, or mutually inconsistent.

**Controls:** provenance preservation, content-hash deduplication, domain/freshness filters, conflict representation, and semantic claim-support verification.

**Residual risk:** search rank is not source trust. The project does not currently perform authoritative-source scoring or independent corroboration beyond gathered evidence.

### CLI credential/authority surface

**Scenario:** convenience code bypasses the core policy or exposes API keys in command history.

**Controls:** CLI uses the same `ResearchService`; API keys come from environment variables rather than command-line options; request/domain/budget validation remains in core models.

## Security-event semantics

`SecurityEvent` is observability, not a verdict system. In particular, `SUSPICIOUS_CONTENT` means a heuristic rule matched and `SEMANTIC_CONTENT_RISK` means the configured semantic-risk event threshold was exceeded. Neither proves an attack, and absence of either event does not establish that content is benign.

## Security regression evidence

Adversarial tests cover prompt injection, role impersonation, secret requests, metadata/SSRF attempts, provenance manipulation, invented references, unexpected action fields, and redirect attacks.

```bash
uv run pytest -m adversarial -v
```

The deterministic [security benchmark](../benchmarks/security/README.md) goes further by assuming the model is already compromised and comparing which forbidden actions the surrounding architectures permit.

## Deployment assumptions

For sensitive deployment, pair application controls with independent egress policy, process/container isolation, secret management, filesystem restrictions, resource limits, and monitoring.

## References

The design is informed by OWASP guidance on prompt injection, AI-agent least privilege, SSRF prevention, and adversarial testing. The project deliberately treats attack detection as defense in depth rather than the primary authorization boundary.

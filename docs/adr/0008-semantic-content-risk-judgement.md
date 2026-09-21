# ADR 0008: Semantic content-risk judgement is observability, not authority

- Status: Accepted
- Date: 2026-09-21

## Context

`safe-web-research` already treats public-web content as untrusted data. The deterministic authority boundary prevents fetched text from gaining arbitrary HTTP, browser, shell, filesystem, secret, or action capabilities. `SuspiciousContentScanner` adds cheap local signals for several explicit prompt-injection-like patterns, but its findings are intentionally not an authorization mechanism.

A semantic model can detect paraphrases and contextual attacks that fixed patterns miss, and can distinguish some quoted/educational prompt-injection text from operative instructions. TypeSafe Jev is designed for narrow typed decisions and is available through OpenRouter's alpha Decisions API. That makes it suitable as a low-cost defense-in-depth signal, but not as a security boundary: a probabilistic judgement can be wrong and the provider can fail.

## Decision

Add a separate provider-neutral `ContentSecurityJudge` abstraction and an OpenRouter Jev
implementation. The runtime remains **observe only**, and the CLI/reference composition enables it
by default with an explicit `off` opt-out. Low-level components do not create a remote judge
implicitly; application composition owns that decision.

The design has these invariants:

1. A semantic judgement never grants authority or converts web content into trusted instructions.
2. A "safe" judgement does not weaken SSRF, provenance, resource, or model-tool boundaries.
3. A risky judgement does not remove or rewrite evidence in observe mode.
4. Judge timeout, provider failure, malformed output, or rate limiting leaves evidence unchanged and emits an observability event.
5. Runtime policy is injected by trusted application configuration, not accepted from `ResearchRequest`.
6. The existing deterministic `SuspiciousContentScanner` remains in place.

Jev receives only bounded public source metadata and selected evidence text. It does not receive API keys, environment variables, system prompts, internal agent state, or arbitrary application secrets.

## Decision model

One Jev request asks five narrow questions over the same source state:

- a Choice classifying content as ordinary content, benign AI/security discussion, operative model instruction, or unclear;
- a Noul for instruction-hierarchy override;
- a Noul for external-capability induction;
- a Noul for secret/protected-data exfiltration;
- a Noul for provenance/citation manipulation.

Trusted Python computes `semantic_risk` as the maximum of the operative-instruction probability and the four independent Noul probabilities. The application does not use Jev Choice `confidence` as an attack probability.

Selected evidence is grouped by source. Each source call is deterministically character-bounded; when truncation is necessary, the sampler preserves both the head and tail of every selected chunk rather than taking only a page prefix. Calls are capped and concurrency-bounded by `ContentJudgementPolicy`.

## Provider choice

The reference adapter uses the pinned OpenRouter model `typesafe/jev-1.13` and `POST /api/alpha/decisions`. The model is pinned because a floating latest alias would make evaluation results change without a code/configuration change. The endpoint is alpha, so the wire response is locally validated and isolated behind the adapter.

## Failure behavior

Provider failures are fail-open **for evidence inclusion only**. This does not mean the system fails open on authority: the pre-existing deterministic boundaries remain unchanged. A failure produces `content_judgement_error`; a risk above the configured threshold produces `semantic_content_risk`.

## Consequences

Positive:

- semantic coverage can complement fixed patterns;
- attack-like quoted documentation can be represented explicitly as a hard-negative class;
- model/provider changes remain isolated;
- probabilities and provider usage can be benchmarked independently from policy;
- Jev failure cannot remove the existing containment guarantees.

Tradeoffs:

- default observe mode adds network latency, provider dependency, and cost to normal reference-CLI
  research unless the caller opts out;
- probabilities require calibration on a project-specific corpus before they should affect evidence inclusion;
- the OpenRouter Decisions API is alpha and may change;
- character sampling is deterministic but can still omit parts of very large selected evidence sets.

## Deferred work

Do not add blocking/quarantine merely because this adapter exists. A filtering mode should be introduced only after a committed benchmark measures false positives and false negatives on real attacks, benign AI/security documentation, quoted attacks, tool documentation, obfuscation, mixed pages, and multilingual cases. Filtering must happen before final evidence sufficiency/selection so rejected evidence can be replaced rather than silently shrinking the final evidence set.

# ADR 0004: Indirect Prompt Injection Is Contained by Authority Separation

## Status

Accepted

## Context

Fetched web pages are untrusted and may contain instructions intended for an LLM rather than information relevant to the user's research question.

No prompt-injection detector is complete. A design that requires perfect detection before giving a model powerful tools fails open when detection misses an attack.

## Decision

The research synthesizer will process untrusted evidence without receiving network, shell, filesystem, browser, or arbitrary tool authority.

Trusted Python code owns all external actions.

The synthesizer may return only a strict structured draft containing:

- an answer,
- claims,
- evidence-ID references,
- conflicts.

Trusted code validates evidence and claim references before constructing a `ResearchResult`.

A deterministic `SuspiciousContentScanner` may flag explicit attack-like patterns for observability. Scanner findings do not block evidence, grant authority, or establish that content is safe.

## Consequences

A successful indirect prompt injection may still influence answer quality.

It cannot, through the synthesizer alone:

- trigger additional fetches,
- access internal network targets,
- read environment credentials,
- execute shell commands,
- mutate files,
- invent trusted evidence objects,
- add arbitrary action fields to a valid result.

This architecture intentionally favors capability containment over reliance on prompt wording or attack detection.

Adversarial regression tests must cover these invariants.

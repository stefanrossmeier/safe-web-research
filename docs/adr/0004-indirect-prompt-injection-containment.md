# ADR 0004: Indirect Prompt Injection Is Contained by Authority Separation

## Status

Accepted

## Context

Fetched pages are untrusted and may contain instructions intended for an LLM rather than information relevant to the user's question.

No prompt-injection detector is complete. A design that requires perfect detection before giving a model powerful tools fails open when detection misses an attack.

## Decision

Fetched/extracted content is always treated as data.

Planner/synthesizer/verifier models receive no network, shell, filesystem, browser, secret, or arbitrary action authority. Trusted Python owns external actions.

The synthesizer may return only a strict structured draft containing an answer, claims, evidence references, and conflicts. Trusted code resolves and validates those references before constructing a `ResearchResult`.

A deterministic `SuspiciousContentScanner` may flag explicit attack-like patterns for observability. Scanner findings do not block evidence, grant authority, or establish that content is safe.

## Consequences

A successful indirect prompt injection may still influence source selection, wording, or factual quality.

It cannot, through the research-model interfaces alone:

- trigger arbitrary extra fetches;
- access internal network targets;
- read environment credentials;
- execute shell commands;
- mutate files;
- invent trusted evidence objects;
- add arbitrary action fields to a valid result.

The scanner will have false positives and false negatives. That is acceptable because containment does not depend on it.

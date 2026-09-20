# ADR 0002: Provider-Neutral Core and Trusted Canonical Identity

## Status

Accepted

## Context

Search and LLM providers differ in wire formats, error shapes, usage reporting, supported parameters, and model behavior. Coupling core research logic to one provider or one model makes security invariants harder to test and portability failures easy to hide.

A concrete portability test also showed that a model can satisfy JSON-Schema output yet still reproduce application-level identifiers unreliably.

## Decision

Search and LLM integrations will sit behind provider-neutral interfaces.

Provider adapters own:

- authentication;
- provider-specific request/response formats;
- provider-specific error normalization;
- usage/cost metadata normalization.

The core owns normalized domain models, orchestration, validation, provenance, and budgets.

Structured LLM responses are validated both through provider JSON-Schema support and again locally.

Canonical application identity remains in trusted code. Where models need to refer to claims/evidence, the core may expose short model-facing references (`Q1`, `E1`, ...) and map them back to canonical IDs after local validation. Core correctness must not depend on a model copying opaque application IDs perfectly.

## Consequences

Compatible providers/models can be tested without changing research orchestration. Provider-specific quirks stay localized.

The interface intentionally does not promise that every OpenRouter model is compatible; live integration tests are used to detect unsupported structured-output behavior or other provider/model assumptions.

Short model-facing references add trusted mapping code, but reduce prompt/token noise and improve portability without weakening canonical-ID validation.

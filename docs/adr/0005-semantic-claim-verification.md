# ADR 0005: Verify Claim Support Separately from Synthesis

## Status

Accepted

## Context

Reference validation proves that a synthesized claim cites evidence that exists and was supplied to the model. It does not prove that the cited text semantically supports the claim.

A model can produce a syntactically valid citation while overstating, combining, or contradicting evidence. Model portability testing also showed that models should not be trusted to reproduce opaque application identifiers exactly.

## Decision

When semantic verification is enabled, the research service performs a separate structured LLM call after synthesis.

For each claim, the verifier receives only:

- a short model-facing claim reference and claim text;
- short model-facing references for evidence already cited by that claim;
- the cited evidence and provenance metadata.

The response schema is dynamically constrained to the references actually supplied. Trusted Python maps those references back to canonical claim/evidence IDs.

The verifier returns one verdict per claim: `supported`, `partial`, `unsupported`, or `contradicted`.

Trusted validation then requires:

- each synthesized claim is verified exactly once;
- no unknown/duplicate claim reference is accepted;
- supporting evidence is a subset of the claim's existing citations;
- supported/partial verdicts contain supporting evidence.

Unsupported/contradicted claims remain visible and become quality signals rather than being silently deleted.

## Consequences

Verification costs an additional LLM call and remains probabilistic. It improves semantic citation observability but is not formal entailment, source truth validation, or independent fact checking.

Short model-facing references improve compatibility and reduce identifier-copy errors while canonical identity remains under trusted control.

The verifier has no tools/network authority and therefore does not expand the capability boundary.

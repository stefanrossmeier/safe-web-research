# ADR 0005: Verify Claim Support Separately from Synthesis

## Status

Accepted

## Context

Reference validation proves that a synthesized claim cites evidence IDs that exist and were supplied to the model. It does not prove that the cited text semantically supports the claim.

A model can produce a syntactically valid citation while overstating, combining, or contradicting the cited evidence.

## Decision

When semantic verification is enabled, the research service performs a separate structured LLM call after synthesis.

For each claim, the verifier receives only:

- the claim ID and claim text,
- evidence chunks already cited by that claim,
- provenance metadata for those chunks.

It returns one structured verdict per claim: `supported`, `partial`, `unsupported`, or `contradicted`.

Trusted Python validates the verifier output. The verifier cannot introduce new claim IDs or evidence IDs. Supporting evidence must be a subset of evidence already cited by the synthesized claim.

Unsupported and contradicted claims are surfaced as quality flags rather than silently removed.

## Consequences

Verification costs an additional LLM call and remains probabilistic. It improves observability and catches semantic citation failures, but it is not formal entailment proof and does not establish real-world truth.

The verifier has no tools or network authority and therefore does not expand the system's capability boundary.

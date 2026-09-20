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

The response schema is dynamically constrained to the references actually supplied. The model returns a `verifications` object keyed by the short claim references (`Q1`, `Q2`, ...); each claim key has its own schema whose supporting-evidence enum contains only evidence cited by that claim. The model therefore cannot select another claim's evidence while remaining schema-valid. Trusted Python maps the short references back to canonical claim/evidence IDs and repeats the subset check after parsing as defense in depth.

The verifier returns one verdict per claim: `supported`, `partial`, `unsupported`, or `contradicted`.

Trusted validation then requires:

- each synthesized claim is verified exactly once;
- no unknown/duplicate claim reference is accepted;
- supporting evidence is a subset of the claim's existing citations;
- supported/partial verdicts contain supporting evidence.

Unsupported/contradicted claims remain visible and become quality signals rather than being silently deleted.

## Consequences

Verification costs an additional LLM call and remains probabilistic. It improves semantic citation observability but is not formal entailment, source truth validation, or independent fact checking.

Claim-keyed structured output avoids asking models to reproduce claim identifiers inside array items, while per-claim evidence enums reduce cross-claim citation mistakes. Short model-facing references improve compatibility while canonical identity remains under trusted control.

The verifier has no tools/network authority and therefore does not expand the capability boundary.

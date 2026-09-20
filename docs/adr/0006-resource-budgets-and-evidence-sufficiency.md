# ADR 0006: Separate Hard Resource Budgets from Soft Evidence Sufficiency

## Status

Accepted

## Context

A generic research capability needs generous enough ceilings for broad questions, but using those ceilings as a target causes unnecessary pages, tokens, latency, and cost. Conversely, setting universally small hard limits harms legitimate research breadth.

An early implementation effectively gathered until the page ceiling and could fetch more material than synthesis would use.

## Decision

Research resource policy has two layers.

### Hard budgets

Trusted code enforces request-level circuit breakers for searches, fetch attempts, successful pages, bytes, redirects, LLM calls, and cumulative token usage. These are security/cost upper bounds and remain configurable.

### Soft evidence sufficiency

A deterministic `EvidenceSelector` ranks/retains evidence using lexical relevance, source diversity, per-source limits, total selected text, and question-term coverage.

Gathering may stop normally before hard limits when the selected evidence set satisfies the configured sufficiency policy. This soft stop does not produce a hard-limit incompleteness flag.

No additional LLM call is used for selection/stopping.

## Consequences

Ordinary research can use substantially fewer pages/tokens than hard budgets permit while difficult/poorly matched research can continue toward the ceiling.

The sufficiency heuristic does not prove semantic completeness and may stop too early or too late on some workloads. It therefore requires live quality/efficiency evaluation in addition to deterministic unit/integration tests.

Hard budgets remain the security boundary; soft sufficiency is an efficiency/quality policy.

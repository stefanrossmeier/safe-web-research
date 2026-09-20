# ADR 0001: Bounded Orchestration Owns Execution Authority

## Status

Accepted

## Context

An Internet-research model consumes attacker-controlled content. If the same model can directly invoke arbitrary HTTP, browser, shell, filesystem, secret, or downstream action tools, successful prompt manipulation can become successful capability escalation.

Prompt wording and injection detection are probabilistic. They are not suitable as the primary authorization boundary.

## Decision

The research core will separate **reasoning** from **authority**.

Models may produce strict structured proposals for bounded stages such as:

- search queries;
- synthesized claims and evidence references;
- claim-support verdicts.

Trusted Python orchestration will own and enforce:

- which external operations exist;
- network target validation and redirects;
- resource budgets;
- canonical source/evidence/claim identity;
- structured-output validation;
- provenance/reference validation;
- stage sequencing.

Research models will not receive arbitrary search/fetch/browser/shell/filesystem/action tools.

Adapters such as the CLI must call the same bounded `ResearchService` rather than reimplementing authority outside the core.

## Consequences

A manipulated model can still degrade research quality. It cannot, through the research-model interface alone, obtain capabilities that the trusted orchestrator never exposes.

This increases explicit orchestration code and limits autonomous tool flexibility. That tradeoff is deliberate: capability containment is preferred over open-ended model agency for this project.

Adding new consequential actions in the future requires revisiting this ADR and the threat model.

# Architecture Decision Records

ADRs capture durable choices that materially affect trust boundaries, provider abstraction, provenance, resource policy, or security tradeoffs. Direct docs describe the **current system**; ADRs explain **why** the system is shaped that way.

| ADR | Status | Decision |
| --- | --- | --- |
| [0001](0001-bounded-orchestration.md) | Accepted | Models propose structured data; trusted orchestration owns authority. |
| [0002](0002-provider-abstractions.md) | Accepted | Keep search/LLM providers behind provider-neutral interfaces and keep canonical identity in trusted code. |
| [0003](0003-ssrf-target-validation.md) | Accepted | Validate DNS/IP targets and pin the connection to validated addresses. |
| [0004](0004-indirect-prompt-injection-containment.md) | Accepted | Contain prompt injection by authority separation; scanner is observability only. |
| [0005](0005-semantic-claim-verification.md) | Accepted | Verify claim support separately and map short model-facing references back to trusted IDs. |
| [0006](0006-resource-budgets-and-evidence-sufficiency.md) | Accepted | Separate hard safety budgets from deterministic soft evidence sufficiency/early stopping. |
| [0007](0007-bounded-http-content-decoding.md) | Accepted | Decode gzip explicitly with compressed/decompressed bounds and fail closed on ambiguous streams. |

## When to add an ADR

Add or revise an ADR when a change alters a durable architectural choice, especially:

- model/tool authority;
- trust boundaries;
- network policy;
- provider abstraction;
- provenance/identity handling;
- resource/cost policy;
- content decoding/execution policy;
- security behavior whose tradeoff is not obvious from code alone.

Do not use ADRs as a changelog for routine refactors or bug fixes that leave the decision intact.

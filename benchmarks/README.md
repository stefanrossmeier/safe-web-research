# Security and research benchmarks

The benchmark suite is intended to compare a bounded research capability with a conventional agent that has direct Internet tool access.

**No comparative benchmark result is claimed yet.** This directory defines the methodology first so later results can be reproduced rather than reverse-engineered from a headline number.

## Comparison configurations

### A. Bounded capability — `safe-web-research`

The model can propose search queries and structured research output, but trusted code owns search/fetch execution, SSRF policy, redirects, budgets, provenance, and verification.

### B. Direct-tool baseline

The same model receives direct search/fetch tools and decides when and where to call them. The baseline should use the same provider model, initial task, source corpus, and comparable resource budget wherever possible.

### C. Optional detector-only baseline

A direct-tool agent with prompt-injection detection but without the deterministic authority boundaries used by `safe-web-research`. This separates the effect of detection from capability containment.

## Benchmark families

1. **Indirect prompt injection** — pages instruct the agent to ignore policy, invoke tools, reveal secrets, or follow attacker-selected URLs.
2. **Network boundary attacks** — loopback/private/link-local targets, cloud metadata, mixed DNS answers, redirect SSRF, DNS-rebinding-style cases.
3. **Provenance attacks** — invented evidence IDs, fake source IDs, citation replacement, action fields smuggled into structured output.
4. **Semantic citation quality** — real evidence IDs that do not actually support the generated claim.
5. **Denial-of-wallet/resource pressure** — loops, oversized responses, excessive queries, redirects, and LLM-call amplification.
6. **Benign control tasks** — ordinary research tasks used to measure whether security controls harm useful completion quality.

## Primary metrics

| Metric | Direction | Meaning |
| --- | --- | --- |
| Attack success rate | lower is better | Fraction of adversarial cases that achieve the forbidden objective. |
| Forbidden network-action rate | lower is better | Attempts/successes to reach disallowed destinations. |
| Invalid provenance acceptance | lower is better | Fabricated or out-of-scope evidence accepted into results. |
| Citation-support failure rate | lower is better | Claims whose cited evidence does not semantically support them. |
| Benign task completion | higher is better | Successful completion on non-adversarial research tasks. |
| Research answer quality | higher is better | Task-specific correctness/relevance score. |
| Cost / tokens / latency | lower is better at equal quality | Operational overhead of each architecture. |
| False-positive security rate | lower is better | Benign inputs incorrectly blocked or degraded. |

## Reproducibility rules

- Pin the LLM model and provider route where possible.
- Record code commit and dependency lockfile.
- Separate deterministic fixture benchmarks from live-web benchmarks.
- Use the same adversarial payloads and benign tasks across compared architectures.
- Publish per-case outcomes, not only aggregate percentages.
- Record token usage, cost, and timing alongside security outcomes.
- Do not treat heuristic prompt-injection detection as equivalent to attack containment.

## Result locations

- [Recorded test runs](../reports/test-runs/README.md)
- [Benchmark results](results/README.md)

Future benchmark artifacts will be committed under `benchmarks/results/` with the exact model, commit, scenario set, and run configuration used.

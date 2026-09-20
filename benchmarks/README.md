# Comparative security containment benchmark

M14 tests the repository's central architectural claim with a reproducible comparison rather than a one-off demo.

The primary question is deliberately narrow:

> **If hostile web content has already influenced the model, what authority can the model exercise through the surrounding architecture?**

This is different from asking whether a particular model detects or resists prompt injection. The benchmark fixes the model's compromised proposal and feeds the same proposal to every compared architecture. That keeps model behavior constant and isolates capability containment.

## Compared architectures

### A. `safe-web-research`

The bounded configuration models the authority actually available to this project:

- arbitrary model-origin URLs are rejected because the model does not own a generic fetch tool;
- search-result URLs are checked with the production `URLPolicy`, including hostname/IP/port rules;
- citations are restricted to evidence IDs already known to trusted code;
- shell commands, secret reads, and arbitrary extra actions are unavailable;
- `SuspiciousContentScanner` findings are recorded but do not become an authority boundary.

### B. Direct-tool baseline

The direct baseline represents the security-relevant property being compared: a compromised model has direct authority to invoke the proposed network, shell, secret, provenance, or extra action. It is intentionally minimal and is **not** presented as a production agent framework.

### C. Detector-only baseline

The detector-only baseline uses this repository's heuristic `SuspiciousContentScanner` as a blocking gate in front of the direct-tool baseline. If the scanner finds a suspicious pattern, the proposal is blocked; otherwise it receives direct authority.

This baseline is useful for separating **detection** from **containment**. It is not claimed to represent every prompt-injection detector.

## Case corpus

The version-1 corpus lives in [`cases/security_containment.json`](cases/security_containment.json). It contains both adversarial cases and benign controls across:

- network/SSRF boundaries;
- arbitrary model-origin network retargeting;
- secret exfiltration;
- shell/tool execution;
- provenance manipulation;
- action smuggling;
- combined attacks;
- benign content, including deliberately scanner-confusing documentation text.

Cases declare three distinct things:

1. the untrusted content the model saw;
2. the fixed model proposal after that content influenced behavior;
3. actions that are required for benign completion and actions that are forbidden.

DNS answers are fixture data. No benchmark case makes a real network request.

## Metrics

The aggregate report includes:

| Metric | Meaning |
| --- | --- |
| Attack success rate | Fraction of adversarial cases where at least one explicitly forbidden action was accepted. |
| Forbidden network execution | Forbidden network targets accepted by the architecture. |
| Secret exfiltration acceptance | Forbidden secret-read requests accepted. |
| Shell-action acceptance | Forbidden shell commands accepted. |
| Invalid provenance acceptance | Unknown/fabricated evidence references accepted. |
| Action-smuggling acceptance | Arbitrary extra actions accepted. |
| Benign completion | Benign cases where all required actions remained available. |
| Benign security-warning rate | Benign cases that triggered the heuristic scanner. |

Runtime is recorded per case, but this benchmark intentionally makes **zero LLM calls**, consumes **zero provider tokens**, and incurs **zero provider cost**. Those values are zero because model behavior is fixed, not because a real research run is free.

## Run it

From a clean repository:

```bash
uv run python -m benchmarks.run_security_benchmark
```

The runner writes timestamped and `latest` Markdown/JSON artifacts under [`results/`](results/README.md).

It refuses to write benchmark artifacts from a dirty Git tree. For local development only:

```bash
uv run python -m benchmarks.run_security_benchmark --allow-dirty
```

Run the deterministic regression coverage separately with:

```bash
uv run python scripts/check.py
```

## Reproducibility and interpretation rules

- Commit the benchmark implementation and case corpus before producing an authoritative result.
- Preserve per-case outcomes, not only aggregate percentages.
- Compare the exact same fixed proposal across architectures.
- Do not add a live LLM to this primary containment benchmark; that would mix model susceptibility with authority containment.
- Do not describe detector-only results as representative of detector products generally.
- Do not extrapolate beyond the committed case corpus.
- Treat heuristic scanner warnings as observability. A warning is not proof of an attack, and no warning is not proof of safety.
- A zero attack-success rate here means the included compromised proposals could not cross the modeled authority boundary. It is not a proof that every possible attack is contained.

## What this benchmark does not measure

The deterministic M14 suite does not establish:

- the probability that a live model follows prompt injection;
- general answer correctness or relevance;
- semantic citation-verifier accuracy on an open-ended corpus;
- live-web provider latency, token usage, or cost;
- robustness to every possible browser protocol or future tool capability.

Those are separate research-quality and robustness evaluations. Keeping them separate makes the M14 security claim easier to interpret and reproduce.

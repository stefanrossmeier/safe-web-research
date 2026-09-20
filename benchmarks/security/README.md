# Security Containment Benchmark

This deterministic benchmark tests one narrow architectural claim:

> **If hostile content has already influenced the model, what authority can the compromised model exercise through the surrounding architecture?**

It fixes model behavior instead of sampling a live LLM. That isolates containment from prompt-injection susceptibility.

## Compared architectures

### `safe-web-research`

Models do not own arbitrary network, shell, secret, provenance, or extra-action authority. Search-result URLs pass the production URL policy and provenance references are constrained to trusted evidence.

### Direct-tool baseline

An intentionally minimal baseline accepts the same proposed actions directly. It models the security-relevant property "compromised model has direct authority"; it is not presented as a production framework.

### Detector-only baseline

The repository's heuristic `SuspiciousContentScanner` blocks proposals it flags; unflagged proposals otherwise receive direct authority. This separates detection from containment and is not representative of all commercial detectors.

## Corpus

[`cases.json`](cases.json) contains adversarial and benign controls across network/SSRF boundaries, arbitrary network retargeting, secret exfiltration, shell/tool execution, provenance manipulation, action smuggling, combined attacks, and benign scanner-confusing text.

Each case defines untrusted content, a fixed post-compromise model proposal, required benign actions, and explicitly forbidden actions. DNS answers are fixtures; the benchmark makes no real network calls.

## Metrics

- attack success;
- forbidden network execution;
- secret-read acceptance;
- shell acceptance;
- invalid provenance acceptance;
- action-smuggling acceptance;
- benign completion;
- benign scanner-warning rate.

Provider token use/cost is zero by construction because the model proposal is fixed.

## Run

From a clean committed revision:

```bash
uv run python -m benchmarks.security
```

Development-only dirty run:

```bash
uv run python -m benchmarks.security --allow-dirty
```

Artifacts are written to [`../../reports/security_benchmark/`](../../reports/security_benchmark/README.md).

## Interpretation limits

A zero attack-success rate means the **committed corpus/proposals** could not cross the modeled authority boundary. It does not prove all prompt injections are prevented or detected.

This benchmark does not measure live-model injection susceptibility, general answer correctness, semantic verifier accuracy, live provider latency/cost, or every future capability/protocol.

# Benchmarks

Benchmarks are executable evaluations, not ordinary pytest regressions and not generated reports.

This directory contains two benchmark packages:

| Benchmark | Purpose | External services | Command |
| --- | --- | --- | --- |
| [security/](security/README.md) | Authority containment after model compromise | none | `uv run python -m benchmarks.security` |
| [research_quality/](research_quality/README.md) | Live research usefulness/efficiency | Brave + OpenRouter + public web | `uv run python -m benchmarks.research_quality --model <model>` |

Each benchmark owns its methodology, case definition, and runner code. Generated evidence is written to [`../reports/`](../reports/README.md), keeping evaluation implementation separate from recorded executions.

Deterministic tests for benchmark code live under `tests/benchmark/`.

## Jev semantic content judgement

`benchmarks/content_judgement/` is a live 40-case Jev evaluation with 20 paired hard benign negatives and 20 operative attacks. It measures semantic separation and produces calibration/reporting artifacts; it is not part of the deterministic default test gate.

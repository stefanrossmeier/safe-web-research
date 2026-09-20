# Benchmark results

Authoritative comparative-security benchmark artifacts are generated from a clean Git commit with:

```bash
uv run python -m benchmarks.run_security_benchmark
```

The runner writes:

```text
benchmarks/results/
    latest.md
    latest.json
    <timestamp>.md
    <timestamp>.json
```

The timestamped pair is the immutable evidence for a specific execution. `latest.*` is a convenience copy of the newest run.

Each artifact records the source commit and per-case outcomes as well as aggregate metrics. The deterministic M14 benchmark makes no live model or network calls: it fixes model behavior and compares what each surrounding architecture permits after compromise. As a result, token and provider-cost fields are zero by construction.

Do not interpret a clean run as proof against all prompt injections. The result is evidence for the committed case corpus and the exact benchmark semantics documented in [`../README.md`](../README.md).

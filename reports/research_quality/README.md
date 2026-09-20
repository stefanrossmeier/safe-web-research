# Research-Quality Reports

Generated from a clean committed revision with a named OpenRouter model, for example:

```bash
uv run python -m benchmarks.research_quality \
  --model z-ai/glm-5.3-flash
```

Reports record per-case pass/fail, expected-term coverage, semantic support, hard-limit flags, pages/fetches, tokens, provider cost, and wall time.

Because the benchmark uses live providers/public web, results are stochastic and must not be presented as a universal model ranking.

Methodology: [`../../benchmarks/research_quality/README.md`](../../benchmarks/research_quality/README.md).

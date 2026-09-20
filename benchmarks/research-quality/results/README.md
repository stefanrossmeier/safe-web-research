# Research-quality results

Authoritative M15 live research-quality artifacts are generated from a clean committed revision with a named OpenRouter model.

For the current low-cost validation model:

```bash
uv run python -m benchmarks.run_research_quality \
  --model z-ai/glm-5.3-flash
```

Commit timestamped and `latest` JSON/Markdown results only after reviewing them. Live-provider results are not deterministic and must not be interpreted as a general ranking of models.

# Live research-quality matrix

This M15 benchmark evaluates the real research pipeline on a small set of unrelated benign tasks. It is intentionally separate from the deterministic M14 security-containment benchmark.

It uses real Brave Search, real web fetching, and a real OpenRouter model. Runs therefore cost money and may vary with search results, provider routing, site availability, latency, and model behavior.

The current matrix covers Python language documentation, HTTPX, Pydantic, OWASP security guidance, and Python API documentation. Each case contains lightweight expected-term anchors. A case passes when:

- a non-empty answer is produced;
- all expected anchor terms appear in the answer or claims;
- every synthesized claim receives a semantic verification;
- no claim is unsupported or contradicted (partial support is allowed); and
- the run does not hit a hard research ceiling or synthesis-evidence truncation.

These checks are regression signals, not a complete semantic answer-quality metric. Human review remains necessary.

## Run with GLM 5.3 Flash

Load credentials first, then run from a **clean committed revision**:

```bash
set -a
source .env
set +a

uv run python -m benchmarks.run_research_quality \
  --model z-ai/glm-5.3-flash
```

The runner refuses authoritative output from a dirty tree. For local development only:

```bash
uv run python -m benchmarks.run_research_quality \
  --model z-ai/glm-5.3-flash \
  --allow-dirty
```

Results are written as timestamped and `latest` Markdown/JSON files under `results/`.

The quality profile uses smaller budgets than the generic research defaults: up to 3 searches, 12 fetch attempts, 6 successful pages, 150k cumulative LLM input tokens, and 20k cumulative LLM output tokens. These are benchmark controls, not production defaults.

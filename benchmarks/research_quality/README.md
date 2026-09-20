# Live Research-Quality Benchmark

This benchmark exercises the real research pipeline on several unrelated benign documentation/security questions. It is intentionally separate from the deterministic security containment benchmark.

It uses real Brave Search, public-web fetching, and a real OpenRouter model, so runs cost money and can vary with provider routing, search results, site availability, latency, and model behavior.

## Cases

[`cases.json`](cases.json) currently covers Python language documentation, HTTPX, Pydantic, OWASP SSRF guidance, and Python API documentation.

Each case includes lightweight expected-term anchors. A case passes when:

- a non-empty answer is produced;
- all expected anchors appear in the answer/claims;
- every synthesized claim receives semantic verification;
- no claim is unsupported/contradicted (partial support is allowed);
- no hard research ceiling or synthesis-evidence truncation is hit.

These checks are regression signals, not a complete semantic quality score.

## Run

Load credentials and run from a clean committed revision:

```bash
set -a
source .env
set +a

uv run python -m benchmarks.research_quality \
  --model z-ai/glm-5.3-flash
```

Development-only dirty run:

```bash
uv run python -m benchmarks.research_quality \
  --model z-ai/glm-5.3-flash \
  --allow-dirty
```

Artifacts are written to [`../../reports/research_quality/`](../../reports/research_quality/README.md).

The benchmark profile intentionally uses smaller ceilings than general CLI defaults: up to 3 searches, 12 fetch attempts, 6 successful pages, 150k cumulative LLM input tokens, and 20k output tokens.

Do not use a single run as a general model ranking. Human review remains necessary for publication claims.

# CLI Reference

The CLI is a thin adapter over `ResearchService`; it does not create a second fetch/search authority path.

## Environment

Required for real research:

```text
BRAVE_API_KEY
OPENROUTER_API_KEY
```

Optional runtime configuration:

```text
OPENROUTER_MODEL
SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT
OPENROUTER_JEV_MODEL
```

If unset, the current runtime default is `openai/gpt-5-mini`. The configured OpenRouter model must support the structured-output requests used by planning/synthesis/verification.

Semantic content judgement defaults to `observe`, so the independent Jev risk judgement runs over
selected evidence during normal CLI research. Observe mode emits telemetry and usage only; it never
filters or trusts evidence. Set `SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT=off` or pass
`--content-judgement off` to opt out.

The Jev model is pinned to `typesafe/jev-1.13` by default and can be overridden explicitly with
`OPENROUTER_JEV_MODEL` or `--jev-model`. Concrete model versions are recommended for reproducible
evaluation.

API keys are intentionally not accepted as CLI flags, reducing accidental disclosure through shell history/process listings.

## Basic usage

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?"
```

Allow one or more discovery domains:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --domain python.org \
  --domain docs.python.org
```

Exclude a domain:

```bash
uv run safe-web-research research \
  "Research Python 3.15" \
  --block-domain example.com
```

Machine-readable output:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --json
```

Skip semantic verification explicitly:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --no-verify
```

Semantic content-risk observability is already enabled by default. Opt out explicitly:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --content-judgement off
```

See [Semantic Content Judgement](semantic-content-judgement.md) for the trust model and failure behavior.

## Budgets

The CLI exposes hard upper bounds:

```text
--max-searches
--max-fetch-attempts
--max-pages
--max-bytes-per-page
--max-total-bytes
--max-redirects
--max-llm-calls
--max-input-tokens
--max-output-tokens
```

Current defaults:

| Option | Default |
| --- | ---: |
| `--max-searches` | 10 |
| `--max-fetch-attempts` | 40 |
| `--max-pages` | 20 |
| `--max-bytes-per-page` | 5,000,000 |
| `--max-total-bytes` | 50,000,000 |
| `--max-redirects` | 5 |
| `--max-llm-calls` | 10 |
| `--max-input-tokens` | 500,000 |
| `--max-output-tokens` | 50,000 |

These are circuit breakers, not a target amount of work. Deterministic evidence sufficiency normally stops suitable research earlier.

Fetch attempts and successful pages are separate. A blocked/failed/unsupported response consumes a fetch attempt but does not consume a successful-page slot.

Verification normally adds a third model call after planning and synthesis. If a budget cannot support the next stage, the result records an explicit incompleteness/quality reason rather than silently exceeding the limit.

## Fetch/content behavior

Real fetched pages still pass the normal network policy. Identity and gzip response bodies are accepted; gzip is decoded incrementally with decompressed-size enforcement. Unsupported encodings fail closed.

## Human output

Human-readable output includes:

- answer;
- claims;
- semantic verdict/confidence;
- cited/supporting evidence IDs;
- source URLs;
- conflicts;
- security events;
- incompleteness/quality flags;
- resource/token/cost usage, including semantic-judgement calls/tokens/cost separately.

Use `--json` for programmatic consumers.

## Exit codes

- `0`: a synthesized answer was produced;
- `1`: bounded research completed without a synthesized answer;
- `2`: configuration/validation/research execution failed;
- `130`: interrupted by the user.

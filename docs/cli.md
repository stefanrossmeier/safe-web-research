# CLI

The CLI is a thin adapter over the same `ResearchService` used by the Python API. It does not bypass fetch policy, budgets, provenance validation, or claim verification.

## Environment

The CLI reads credentials from environment variables:

```text
BRAVE_API_KEY
OPENROUTER_API_KEY
```

The model defaults to `openai/gpt-5-mini` and can be overridden with either:

```text
OPENROUTER_MODEL
```

or the `--model` option.

The CLI intentionally does not accept API keys as command-line arguments, avoiding accidental disclosure through shell history or process listings.

## Basic usage

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?"
```

Restrict discovery to one or more domains:

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

Emit the complete result as JSON:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --json
```

Skip semantic claim verification:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --no-verify
```

## Budgets

The CLI exposes explicit limits:

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

The defaults are deliberately generous circuit breakers rather than a target research shape: 10 searches, 40 fetch attempts, 20 successfully fetched pages, 5 MB per page, 50 MB total download, 10 LLM calls, 500,000 cumulative input tokens, and 50,000 cumulative output tokens. `max_fetch_attempts` and `max_pages` are separate so blocked or failed fetches do not consume the successful-page budget. All remain hard upper bounds and can be lowered per request.

Verification is enabled by default and normally requires a third LLM call after planning and synthesis. Planner, synthesis, and verification still have bounded per-call completion caps, but the verifier no longer predicts its allowance from the number of synthesized claims. With the default global output budget, synthesis and verification each receive a generous bounded allowance.

The generic hard budgets remain generous circuit breakers. Before synthesis, deterministic trusted code selects a smaller relevance- and diversity-oriented evidence set and can stop gathering early once that set is sufficient. The current selector retains at most 200,000 characters, while synthesis still has a separate 400,000-character safety cap. If evidence nevertheless exceeds the synthesis cap, the result includes `evidence_truncated_for_synthesis`.

The fetcher accepts identity and gzip responses. Gzip is decompressed incrementally and the page-size limit applies to decompressed content; unsupported encodings fail closed.

## Exit codes

- `0`: a synthesized answer was produced,
- `1`: the bounded run completed but no synthesized answer was produced,
- `2`: configuration, validation, or research execution failed,
- `130`: interrupted by the user.

## Human output

Human output shows:

- answer,
- claims,
- support verdict and verifier confidence,
- evidence IDs,
- source URLs,
- conflicts,
- security events,
- incomplete/quality flags,
- resource and cost usage.

For programmatic consumers prefer `--json`.

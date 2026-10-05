# Changelog

## Unreleased

## 0.2.0 — 2026-10-05

Agent integration, citation-preserving handoff, and live observability.

### Highlights

- Add a local tool-using research-agent example that exposes `safe-web-research` as its only web
  authority, with bounded official, recent, regional, and open-web capability profiles.
- Add a five-case live `agent_usage` benchmark covering capability selection, multi-scope
  orchestration, citation quality, latency, Brave/fetch usage, nested LLM stages, and tracked cost.
- Add compact/full research profiles and per-stage timing diagnostics for interactive agent
  experiments without changing the package's core research defaults.
- Make `openai/gpt-6-luna` the default runtime, example-agent, and live-test model after local
  exploratory measurements showed materially lower latency and tracked cost than the earlier
  GPT-5 Mini/GLM experiments.
- Preserve claim-to-source URL provenance through outer-agent finalization so comparative answers
  retain independently supporting citations.
- Make live agent benchmark failures case-local, expose search-provider errors, and suppress
  redundant same-scope research calls rather than aborting or double-counting the suite.
- Enable Jev semantic content judgement by default in observe-only mode, with explicit `off`
  opt-out.
- Add and document the 40-case semantic content-judgement evaluation corpus and recorded results.

## 0.1.0 — 2026-09-20

Initial public release of safe-web-research.

### Highlights

- Bounded web research with explicit resource budgets
- SSRF-resistant fetching with DNS and redirect validation
- Safe bounded gzip decoding
- Provenance-aware evidence collection and citation handling
- Deterministic evidence selection and sufficiency-based stopping
- Structured planning, synthesis, and semantic claim verification
- Claim-scoped verifier evidence constraints
- OpenRouter model abstraction
- Tested during development with GPT-5 Mini, GLM 5.3 Flash, and DeepSeek V4.1 Flash
- Deterministic adversarial containment benchmark
- Reproducible live research-quality and test-run reports
- Standalone CLI and Python package
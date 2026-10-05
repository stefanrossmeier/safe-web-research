# Changelog

## Unreleased

- Make `openai/gpt-6-luna` the default runtime/example-agent model after local agent-usage measurements showed materially lower latency and tracked cost than the previous GPT-5 Mini/GLM experiments.
- Preserve claim-to-source URL provenance in the example research agent so comparative answers can cite multiple independently supporting sources instead of losing source diversity during outer-agent finalization.
- Enable Jev semantic content judgement by default in observe-only mode, with explicit `off`
  opt-out.
- Add and document the 40-case semantic content-judgement evaluation corpus and recorded
  results.

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
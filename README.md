# safe-web-research

Bounded, provenance-aware web research for AI systems.

`safe-web-research` is a small reference implementation for a specific security problem: an AI system needs information from the public Internet, but Internet content is untrusted and may try to manipulate the model that reads it.

The project therefore keeps **authority in trusted Python code**. Models may plan searches, summarize evidence, and verify claims, but they do not receive arbitrary HTTP, browser, shell, filesystem, or action tools.

> **Security goal:** even if hostile web content successfully influences a model, that influence should not automatically become internal-network access, secret access, arbitrary network calls, shell execution, filesystem mutation, fabricated provenance, or unbounded resource use.

## How it works

```text
question
  |
  v
planner LLM -> structured search queries
  |
  v
trusted Python orchestration
  +-- Brave Search
  +-- SSRF-resistant SafeFetcher
  +-- static extraction
  +-- deterministic evidence selection / stopping
  |
  v
synthesizer LLM -> claims + evidence references
  |
  v
trusted reference validation
  |
  v
verifier LLM -> support verdicts
  |
  v
ResearchResult
```

Key controls include DNS/IP validation, validated-address pinning, manual redirect validation, bounded gzip decoding, hard resource budgets, source/evidence provenance, strict structured outputs, and claim-support verification. Prompt-injection scanning exists for observability, not as the authorization boundary.

## Quick start

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), a Brave Search API key, and an OpenRouter API key.

```bash
uv sync
cp .env.example .env
```

Load your local credentials and run one bounded research request:

```bash
set -a
source .env
set +a

uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --domain python.org
```

For setup, JSON output, budget controls, live tests, and Python usage, see **[Quickstart](docs/QUICKSTART.md)**.

## What is included

- provider-neutral search and LLM interfaces with Brave Search and OpenRouter implementations;
- SSRF-resistant HTTP(S) fetching with DNS/IP policy and validated-address pinning;
- bounded identity/gzip response handling and static HTML/text extraction;
- deterministic evidence selection, source diversity, and early stopping below hard budgets;
- provenance-preserving sources and evidence chunks;
- structured planning, synthesis, and semantic claim verification;
- deterministic, integration, adversarial, and opt-in live tests;
- a deterministic compromised-model containment benchmark;
- a paid live research-quality/efficiency benchmark;
- a standalone CLI and Python API.

The project is a **pre-1.0 reference implementation**, not an audited security product. It does not claim perfect prompt-injection detection, factual correctness, formal entailment, or protection from a compromised host runtime.

## Evidence

The repository keeps executable evaluations separate from generated evidence:

- [Security containment benchmark](benchmarks/security/README.md) → [recorded results](reports/security_benchmark/README.md)
- [Live research-quality benchmark](benchmarks/research_quality/README.md) → [recorded results](reports/research_quality/README.md)
- [Recorded test runs](reports/test_runs/README.md)

The current deterministic containment benchmark records zero accepted forbidden actions for `safe-web-research` across its committed adversarial corpus. That is evidence for that corpus and benchmark model, not proof against all future attacks.

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [CLI reference](docs/cli.md)
- [Testing and evaluation](docs/testing.md)
- [Repository layout](docs/repository-layout.md)
- [Architecture decision records](docs/adr/README.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

Apache-2.0. See [LICENSE](LICENSE).

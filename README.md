# safe-web-research

[![CI](https://github.com/stefanrossmeier/safe-web-research/actions/workflows/ci.yml/badge.svg)](https://github.com/stefanrossmeier/safe-web-research/actions/workflows/ci.yml)

Bounded, provenance-aware web research for AI systems.

`safe-web-research` is a reference implementation for a specific security problem: an AI system
needs information from the public Internet, but Internet content is untrusted and may try to
manipulate the model that reads it.

The project keeps **authority in trusted Python code**. Models may plan searches, summarize
evidence, and verify claims, but they do not receive arbitrary HTTP, browser, shell, filesystem, or
action tools.

> **Security goal:** even if hostile web content influences a model, that influence should not
> automatically become internal-network access, secret access, arbitrary network calls, shell
> execution, filesystem mutation, fabricated provenance, or unbounded resource use.

## How it works

```text
question
  -> planner LLM (structured search queries)
  -> trusted Python orchestration
       -> Brave Search
       -> SSRF-resistant SafeFetcher
       -> static extraction
       -> deterministic evidence selection / stopping
       -> Jev semantic judgement (default observe-only)
  -> synthesizer LLM (claims + evidence references)
  -> trusted reference validation
  -> verifier LLM (claim-scoped support verdicts)
  -> ResearchResult
```

Key controls include DNS/IP validation, validated-address pinning, manual redirect validation,
bounded gzip decoding, hard resource budgets, provenance checks, strict structured outputs,
claim-support verification, and default-on semantic content-risk observability with Jev.
Prompt-injection detection remains defense in depth, not the authorization boundary.

## When to use it

Use this project when an application or agent needs **bounded public-web research** with explicit
network, provenance, and resource controls. It is designed as a security-oriented reference
architecture that can be embedded behind a larger agent system.

It is **not** a general browser agent, an autonomous deep-research product, or a prompt-injection
detector. It deliberately gives the model less authority than those systems often do.

## Quick start

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), a Brave Search API key, and an
OpenRouter API key.

```bash
uv sync
cp .env.example .env

set -a
source .env
set +a

uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --domain python.org
```

For setup, JSON output, budget controls, live tests, and Python usage, see
**[Quickstart](docs/QUICKSTART.md)**.

## Example result

Abridged CLI output has this shape:

```text
Answer:
<concise answer synthesized from the bounded evidence set>

Claims:
- [supported] <claim>
  supporting: evidence-...

Sources:
- <source title> — https://...
```

The complete result can also be emitted as JSON with `--json`, including provenance, verification,
security events, incomplete/quality flags, and resource usage.

## What is included

- provider-neutral search and LLM interfaces with Brave Search and OpenRouter implementations;
- SSRF-resistant HTTP(S) fetching with DNS/IP policy and validated-address pinning;
- bounded identity/gzip response handling and static HTML/text extraction;
- deterministic evidence selection, source diversity, and early stopping below hard budgets;
- Jev-based semantic content-risk judgement, enabled by default in observe-only mode;
- provenance-preserving sources/evidence and claim-scoped semantic verification;
- deterministic, integration, adversarial, and opt-in live tests;
- deterministic security and paid live research-quality benchmarks;
- a standalone CLI and Python API.

This is a **pre-1.0 reference implementation**, not an audited security product. It does not claim
perfect prompt-injection detection, factual correctness, formal entailment, or protection from a
compromised host runtime.

## Evidence

Executable evaluations live under [`benchmarks/`](benchmarks/README.md); recorded release evidence
lives under [`reports/`](reports/README.md). The current deterministic containment benchmark records
zero accepted forbidden actions for `safe-web-research` across its committed adversarial corpus.
That is evidence for the committed corpus and benchmark semantics, not proof against all future
attacks.

The recorded [40-case Jev semantic evaluation](reports/content_judgement/latest.md) contains 20
hard benign negatives and 20 operative attacks. At the descriptive `0.85` threshold it recorded
`20 TP / 20 TN / 0 FP / 0 FN`; the highest benign risk was `0.64` and the lowest malicious risk
was `0.98`. The same corpus caused the deterministic regex scanner to flag 14/20 benign cases
and 15/20 malicious cases. The complete Jev run cost about `$0.00154`. These are recorded
evaluation results, not a general security guarantee or authorization policy.

For release evidence, all report families are regenerated from one clean commit with
`scripts/record_release_evidence.py`; see [Testing and evaluation](docs/testing.md).

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [Semantic content judgement](docs/semantic-content-judgement.md)
- [CLI reference](docs/cli.md)
- [Testing and evaluation](docs/testing.md)
- [Repository layout](docs/repository-layout.md)
- [Architecture decision records](docs/adr/README.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Support and maintenance

For bugs and feature requests, use [GitHub Issues](https://github.com/stefanrossmeier/safe-web-research/issues).
For vulnerabilities, follow [SECURITY.md](SECURITY.md) rather than opening a public issue. The
project is maintained by [@stefanrossmeier](https://github.com/stefanrossmeier) as a reference and
portfolio project; no support SLA is provided.

## License

Apache-2.0. See [LICENSE](LICENSE).

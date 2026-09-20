# safe-web-research

A bounded, provenance-aware web research reference implementation for Python.

`safe-web-research` treats the Internet as hostile input. Search results, DNS responses, redirects, HTML, extracted text, and LLM outputs are all untrusted. Models can propose structured research decisions, but trusted Python code owns network access, budgets, provenance, and validation.

> **Status:** pre-1.0 reference implementation. The Python API is functional and covered by deterministic, adversarial, and opt-in live tests. CLI, REST, MCP, container packaging, and Safeplane integration are intentionally deferred.

## Why this project exists

Giving an LLM unrestricted browser or HTTP tools creates a large attack surface:

- indirect prompt injection from fetched pages,
- SSRF and cloud-metadata access,
- DNS rebinding and redirect bypasses,
- secret or query exfiltration,
- fabricated citations,
- unbounded searches, downloads, and model calls.

This project explores a different architecture: **the LLM does not own tools**. A trusted orchestrator executes only bounded operations through narrow provider interfaces.

## Security model

The central invariant is:

> If hostile web content successfully manipulates a research model, it may degrade the quality of the answer, but it must not thereby gain access to secrets, internal network destinations, filesystem mutation, arbitrary tools, or consequential external actions.

Important controls include:

- only `http` and `https` fetching on standard ports,
- DNS resolution before connection and rejection of non-global addresses,
- validated-address connection pinning to reduce DNS-rebinding/TOCTOU risk,
- manual redirect handling with full validation at every hop,
- no environment-proxy inheritance in the fetcher,
- bounded response sizes and redirect counts,
- restricted content types and no compressed responses in V1,
- deterministic static text extraction,
- LLM providers behind a provider-neutral interface,
- JSON-Schema structured output plus local validation,
- claim citations restricted to evidence IDs created by trusted code,
- search/page/byte/model/token budgets,
- heuristic suspicious-content detection for observability only,
- adversarial fixtures covering indirect prompt injection, provenance poisoning, and SSRF.

The suspicious-content scanner is **not** a security boundary. It can miss attacks and may produce false positives. The primary defense is capability containment.

## Architecture

```text
ResearchRequest
      |
      v
ResearchPlanner (LLM, structured output only)
      |
      | search queries
      v
trusted ResearchService
      |
      v
EvidenceGatherer
      |
      +--> SearchProvider ----> Brave Search
      |
      +--> SafeFetcher
      |      |
      |      +--> URL/DNS/IP policy
      |      +--> validated-address pinning
      |      +--> manual redirects
      |      +--> byte/MIME limits
      |
      +--> WebExtractor
      |
      +--> SuspiciousContentScanner
      |      (observability only)
      |
      v
EvidenceBundle
      |
      v
ResearchSynthesizer (LLM, no tools)
      |
      v
trusted reference validation
      |
      v
ResearchResult
```

See [Architecture](docs/architecture.md), [Threat Model](docs/threat-model.md), and [Testing](docs/testing.md) for details.

## Current capabilities

- Brave Search provider with normalized results.
- SSRF-resistant bounded HTTP fetcher.
- Static HTML and plain-text extraction.
- Provenance-preserving `Source` and `EvidenceChunk` models.
- Search, page, byte, redirect, LLM-call, and token budgets.
- OpenRouter LLM provider with structured-output validation.
- Bounded two-stage planning and synthesis.
- Evidence-ID validation preventing fabricated citations from entering a result.
- Heuristic indirect-prompt-injection observability.
- Deterministic fake providers for tests.
- Opt-in live integration tests against real services.
- Dedicated adversarial security tests.

## Requirements

- Python 3.12+
- `uv`
- Brave Search API key for live search/research tests
- OpenRouter API key for live LLM/research tests

The deterministic suite does not require credentials or network access.

## Setup

```bash
uv sync
cp .env.example .env
```

Populate `.env` locally:

```text
BRAVE_API_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_TEST_MODEL=openai/gpt-5-mini
```

Never commit `.env`.

Load it into the current shell when running live tests:

```bash
set -a
source .env
set +a
```

## Python example

```python
import asyncio
import os

from safe_web_research.domain import ResearchBudget, ResearchRequest
from safe_web_research.extraction import WebExtractor
from safe_web_research.fetch import SafeFetcher, SystemDNSResolver, URLPolicy
from safe_web_research.llm import OpenRouterLLMProvider
from safe_web_research.research import (
    EvidenceGatherer,
    ResearchPlanner,
    ResearchService,
    ResearchSynthesizer,
)
from safe_web_research.search import BraveSearchProvider


async def main() -> None:
    llm = OpenRouterLLMProvider(
        os.environ["OPENROUTER_API_KEY"],
        model=os.environ["OPENROUTER_TEST_MODEL"],
    )

    service = ResearchService(
        ResearchPlanner(llm),
        EvidenceGatherer(
            BraveSearchProvider(os.environ["BRAVE_API_KEY"]),
            SafeFetcher(URLPolicy(SystemDNSResolver())),
            WebExtractor(),
        ),
        ResearchSynthesizer(llm),
    )

    result = await service.research(
        ResearchRequest(
            question="What changed in Python 3.15?",
            budget=ResearchBudget(
                max_searches=3,
                max_pages=5,
                max_llm_calls=2,
            ),
        )
    )

    print(result.model_dump_json(indent=2))


asyncio.run(main())
```

## Testing

Run the deterministic suite:

```bash
uv run ruff check .
uv run mypy src
uv run pytest -m "not live" -q
```

Run the adversarial suite explicitly:

```bash
uv run pytest -m adversarial -v
```

Run real external integrations:

```bash
set -a
source .env
set +a

uv run pytest tests/live -m live -v
```

Live tests are intentionally excluded from normal CI-style runs because they require credentials, cost money, and depend on external service availability.

## Result model

A successful `ResearchResult` contains:

- `answer`
- `claims`, each referencing one or more trusted `evidence_ids`
- `sources`
- `evidence`
- `conflicts`
- `security_events`
- `usage`
- `incomplete_reasons`

The service may return an incomplete result instead of silently exceeding configured budgets.

## What this project does not claim

This project does **not** claim that:

- prompt injection can be perfectly detected,
- fetched information is necessarily true,
- a cited chunk necessarily proves every semantic nuance of a claim,
- LLM outputs are deterministic,
- application-layer controls replace network/container isolation,
- this pre-1.0 project is production-ready for sensitive deployments.

The current design is a reference architecture demonstrating bounded authority, provenance, and testable security properties.

## Project layout

```text
src/safe_web_research/
  domain/       strict provider-neutral models
  search/       search provider abstraction + Brave
  fetch/        DNS/IP policy + bounded SafeFetcher
  extraction/   HTML/text extraction
  llm/          provider abstraction + OpenRouter
  research/     budgets, planning, gathering, synthesis, orchestration
  security/     suspicious-content observability

tests/
  unit/         deterministic component tests
  integration/  deterministic multi-component tests
  adversarial/  security regression scenarios
  live/         opt-in real-service tests

fixtures/
  adversarial/  hostile external-content fixtures

docs/
  architecture.md
  threat-model.md
  testing.md
  adr/
```

## Development principles

1. The model is not an authorization mechanism.
2. Internet-derived content is untrusted data.
3. Trusted code owns network and resource authority.
4. Provider responses are normalized and validated.
5. Security-sensitive behavior must be covered by deterministic tests.
6. Live-provider behavior supplements rather than replaces deterministic testing.
7. Security detectors provide observability; they do not replace containment.

See [CONTRIBUTING.md](CONTRIBUTING.md) before changing security-sensitive code.

## License

Apache License 2.0.

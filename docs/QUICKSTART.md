# Quickstart

This guide takes a fresh clone to a real bounded research request. For design details, see [Architecture](architecture.md) and the [Threat Model](threat-model.md).

## 1. Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- Brave Search API key
- OpenRouter API key

The no-cost deterministic/adversarial test suite does not require API keys.

## 2. Install

```bash
uv sync
cp .env.example .env
```

Edit `.env` locally. A practical low-cost configuration is:

```text
BRAVE_API_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=z-ai/glm-5.3-flash
SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT=observe
OPENROUTER_JEV_MODEL=typesafe/jev-1.13
OPENROUTER_TEST_MODEL=z-ai/glm-5.3-flash
OPENROUTER_JEV_TEST_MODEL=typesafe/jev-1.13
```

The project is not tied to that model. The provider boundary is designed for compatible OpenRouter models that support the structured-output contract used here.

Never commit `.env`.

Load the file into the current shell:

```bash
set -a
source .env
set +a
```

## 3. Run a research request

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --domain python.org
```

The human-readable result includes:

- synthesized answer;
- claims and semantic support verdicts;
- evidence IDs and source URLs;
- conflicts;
- security events;
- incompleteness/quality flags;
- searches, fetches, pages, token use, and estimated provider cost.

Restrict discovery to multiple domains by repeating `--domain`:

```bash
uv run safe-web-research research \
  "How does strict validation work in Pydantic?" \
  --domain docs.pydantic.dev \
  --domain pydantic.dev
```

Use `--json` for the complete machine-readable `ResearchResult`:

```bash
uv run safe-web-research research \
  "What is asyncio.TaskGroup?" \
  --domain docs.python.org \
  --json
```

Semantic claim verification is enabled by default. `--no-verify` skips the final verification call when you explicitly want the cheaper planner/gatherer/synthesizer path.

Semantic content-risk judgement runs by default in independent Jev `observe` mode. It records
typed semantic risk signals and separate decision-model usage/cost without making low-risk content
trusted or removing high-risk content. No extra flag is required for the normal command above.

Opt out explicitly when you do not want the additional decision-model calls:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --domain python.org \
  --content-judgement off
```

You can also set `SAFE_WEB_RESEARCH_CONTENT_JUDGEMENT=off`. Existing `.env` files created from an
older example may still contain `off`; remove that override or change it to `observe` to receive
the new default. See [Semantic Content Judgement](semantic-content-judgement.md).

See [CLI reference](cli.md) for all filters and budget options.

## 4. Understand the safety model

The CLI is not a browser agent. Search/fetch authority stays in trusted code:

- model-generated output does not directly choose arbitrary HTTP destinations;
- search-result and redirect URLs pass URL/DNS/IP policy;
- fetched text remains untrusted evidence;
- models do not receive shell/filesystem/browser tools;
- source/evidence references are checked by trusted code;
- hard budgets cap network and LLM resource use;
- deterministic evidence selection can stop ordinary research before those ceilings.

Read [Architecture](architecture.md), [Threat Model](threat-model.md), and the [ADR index](adr/README.md) before extending the authority surface.

## 5. Run the local quality gates

The standard no-cost command is:

```bash
uv run python scripts/check.py
```

It runs Ruff formatting/linting, mypy, deterministic tests, and the adversarial suite.

With credentials loaded, include real provider tests:

```bash
uv run python scripts/check.py --include-live
```

Run one deliberately smaller paid end-to-end smoke request:

```bash
uv run python scripts/research_smoke.py
```

See [Testing and evaluation](testing.md) for benchmark and report commands.

## 6. Python API

The CLI is a thin wrapper around the same `ResearchService` available to Python callers:

```python
import asyncio
import os

from safe_web_research.domain import ResearchRequest
from safe_web_research.extraction import WebExtractor
from safe_web_research.fetch import SafeFetcher, SystemDNSResolver, URLPolicy
from safe_web_research.llm import OpenRouterLLMProvider
from safe_web_research.research import (
    EvidenceGatherer,
    ResearchPlanner,
    ResearchService,
    ResearchSynthesizer,
    ResearchVerifier,
)
from safe_web_research.search import BraveSearchProvider


async def main() -> None:
    llm = OpenRouterLLMProvider(
        os.environ["OPENROUTER_API_KEY"],
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-5-mini"),
    )

    service = ResearchService(
        ResearchPlanner(llm),
        EvidenceGatherer(
            BraveSearchProvider(os.environ["BRAVE_API_KEY"]),
            SafeFetcher(URLPolicy(SystemDNSResolver())),
            WebExtractor(),
        ),
        ResearchSynthesizer(llm),
        ResearchVerifier(llm),
    )

    result = await service.research(ResearchRequest(question="What changed in Python 3.15?"))
    print(result.model_dump_json(indent=2))


asyncio.run(main())
```

The Python composition API is deliberately explicit so trust boundaries remain visible.

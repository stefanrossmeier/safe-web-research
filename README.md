# safe-web-research

A bounded, provenance-aware Internet research capability for AI systems.

As AI systems move from passive text generation to autonomous research and tool use, web content is no longer merely something a human reads. It can become input to a decision loop with network access, credentials, budgets, and downstream actions. That creates a new attack surface—and a clear incentive to publish content designed to manipulate agents rather than people: indirect prompt injection, SSRF targets, secret-exfiltration instructions, citation poisoning, scope expansion, and denial-of-wallet loops.

`safe-web-research` was built around a simple architectural response:

> **Treat the Internet as hostile data, and keep authority in deterministic code rather than in the model.**

Models may propose bounded research decisions and synthesize evidence. They do not receive arbitrary browser, HTTP, shell, filesystem, or action tools. Trusted Python code owns network destinations, redirects, budgets, provenance, structured-output validation, and claim-support checks.

> **Status:** pre-1.0 reference implementation. The Python API and standalone CLI are functional and covered by deterministic, adversarial, and opt-in live tests. REST, MCP, container packaging, and Safeplane integration are intentionally deferred until the standalone capability is published and benchmarked.

## Why this architecture

A conventional research agent is often implemented as:

```text
LLM
  |
  +--> search tool
  +--> fetch/browser tool
  +--> arbitrary follow-up tool calls
```

That design makes model behavior part of the authorization boundary. If hostile content successfully changes the model's intentions, the same model may also control where the system connects, what it retrieves next, how much it spends, or which provenance it returns.

`safe-web-research` separates **reasoning authority** from **execution authority**:

```text
LLM proposes structured data
          |
          v
trusted Python validates it
          |
          v
bounded operation executes
```

The model may still be manipulated into producing a poor answer. The security objective is narrower and more testable: **successful model manipulation must not automatically become successful capability escalation.**

## Threats covered

The current implementation has explicit controls and regression tests for:

- indirect prompt injection embedded in fetched content,
- fake `SYSTEM` / `DEVELOPER` instructions in web pages,
- instructions to reveal credentials or environment secrets,
- requests to fetch attacker-selected internal or cloud-metadata URLs,
- SSRF through loopback/private/link-local destinations,
- redirect-based SSRF,
- DNS-rebinding/TOCTOU-style hostname changes,
- mixed public/private DNS answers,
- fabricated evidence IDs and provenance manipulation,
- structured-output field smuggling,
- claims that cite real evidence IDs without actually being supported by that evidence,
- unbounded searches, pages, redirects, response bytes, model calls, and output tokens.

See the full [Threat Model](docs/threat-model.md).

## Security invariant

The central invariant is:

> If hostile web content successfully manipulates a research model, it may degrade answer quality or correctness, but it must not thereby obtain secrets, internal network access, arbitrary network destinations, filesystem mutation, arbitrary tools, or consequential external actions.

This is enforced primarily by architecture, not by asking the model to recognize attacks.

Heuristic prompt-injection detection and semantic claim verification are useful defense-in-depth signals. Neither is treated as an authorization mechanism.

## Architecture

```text
ResearchRequest
      |
      v
ResearchPlanner (LLM, structured output only)
      |
      | search queries only
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
      |      +--> URL / DNS / IP policy
      |      +--> validated-address pinning
      |      +--> manual redirect validation
      |      +--> MIME / byte / redirect limits
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
trusted evidence-reference validation
      |
      v
ResearchVerifier (LLM, no tools)
      |
      | claim + only the evidence already cited by that claim
      v
trusted verification-reference validation
      |
      v
ResearchResult
```

Detailed design documentation:

- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [Testing strategy](docs/testing.md)
- [CLI](docs/cli.md)
- [Architecture decisions](docs/adr/)

## Current capabilities

- Brave Search provider with normalized provider-neutral results.
- SSRF-resistant HTTP fetcher with DNS/IP policy and validated-address pinning.
- Manual redirect validation at every hop.
- Static HTML/plain-text extraction without JavaScript execution.
- Provenance-preserving `Source` and `EvidenceChunk` models.
- Search/fetch-attempt/page/byte/redirect/LLM/token budgets.
- OpenRouter LLM provider with JSON-Schema structured output and local validation.
- Bounded planning, gathering, synthesis, and semantic claim verification.
- Evidence-ID validation preventing fabricated citations from entering a result.
- Claim-support verdicts: `supported`, `partial`, `unsupported`, `contradicted`.
- Suspicious-content events for prompt-injection-like content.
- Deterministic fake providers for repeatable testing.
- Dedicated adversarial security regression suite.
- Opt-in real-service end-to-end tests.
- Standalone CLI with human-readable and JSON output.

## Evidence, tests, and benchmarks

Security claims should be backed by reproducible artifacts rather than screenshots or one-off demos.

### Recorded test runs

The repository includes a test-run recorder that captures commit-bound statistics for Ruff formatting/linting, mypy, non-overlapping deterministic tests, adversarial tests, and optionally live-provider tests:

```bash
uv run python scripts/record_test_run.py
```

Include real external integrations:

```bash
set -a
source .env
set +a

uv run python scripts/record_test_run.py --include-live
```

It writes machine-readable and human-readable results under [`reports/test-runs/`](reports/test-runs/README.md), including pass/fail/skip counts, durations, git commit, dirty-state, Python/platform information, and the configured live-test model. Secrets are not recorded.

For a release, the intent is to commit the timestamped report produced from a clean release commit.

### Comparative security benchmark

The repository includes a deterministic **compromised-model containment benchmark** comparing three architectures:

1. `safe-web-research` with bounded authority, real URL-policy validation, provenance allow-listing, and no shell/secret/arbitrary-action capability;
2. a minimal direct-tool baseline that accepts the same fixed model proposal;
3. a detector-only baseline that uses this repository's heuristic suspicious-content scanner as a blocking gate but otherwise exposes direct authority.

The benchmark intentionally assumes hostile web content has already influenced the model. This isolates the architectural question: **what can a compromised model actually cause the surrounding system to do?** It does not measure the probability that a live model follows a prompt injection.

Run it without API keys or network access:

```bash
uv run python -m benchmarks.run_security_benchmark
```

The runner refuses to publish results from a dirty Git tree unless `--allow-dirty` is explicitly supplied for development. It writes timestamped and `latest` JSON/Markdown artifacts under [`benchmarks/results/`](benchmarks/results/README.md).

The containment suite measures attack success, forbidden network execution, secret/shell/action acceptance, invalid provenance acceptance, benign completion, and benign scanner-warning rates. Because model behavior is fixed rather than sampled, provider token usage and cost are zero by construction; live answer quality, semantic support, and research cost remain separate evaluation dimensions.

See [`benchmarks/README.md`](benchmarks/README.md) for methodology, corpus design, interpretation limits, and reproduction instructions. Comparative claims should cite a committed benchmark artifact generated from a clean commit rather than extrapolating beyond the case corpus.

## Requirements

- Python 3.12+
- `uv`
- Brave Search API key for real search/research
- OpenRouter API key for real LLM/research

Deterministic and adversarial suites do not require real credentials or public Internet access.

## Setup

```bash
uv sync
cp .env.example .env
```

Populate `.env` locally:

```text
BRAVE_API_KEY=...
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=openai/gpt-5-mini
OPENROUTER_TEST_MODEL=openai/gpt-5-mini
```

Never commit `.env`.

Load it into the current shell when running the real capability or live tests:

```bash
set -a
source .env
set +a
```

## CLI quickstart

Run one bounded research request:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --domain python.org
```

The human-readable output includes the answer, claims, semantic support verdicts, evidence IDs, sources, conflicts, security events, quality/incompleteness flags, and usage/cost statistics.

For the complete machine-readable result:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --domain python.org \
  --json
```

Verification is enabled by default. To compare the cheaper planner/gatherer/synthesizer path:

```bash
uv run safe-web-research research \
  "What changed in Python 3.15?" \
  --domain python.org \
  --no-verify
```

See [CLI documentation](docs/cli.md) for filters and budget controls.

The default research budget is intentionally generous and acts as a circuit breaker rather than a recipe for how much work every request should perform. Fetch attempts are tracked separately from successfully fetched pages, so blocked, unsupported, or failed responses do not consume the successful-page budget. The default limits can be lowered per request, while model validation still enforces absolute upper bounds. If gathered evidence exceeds the synthesis context cap, the result reports `evidence_truncated_for_synthesis`.

## Python example

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

    result = await service.research(
        ResearchRequest(
            question="What changed in Python 3.15?",
        )
    )

    print(result.model_dump_json(indent=2))


asyncio.run(main())
```

## Semantic claim verification

Citation integrity and citation support are different problems.

Trusted code can prove that an ID such as `evidence-123` exists and was included in the synthesis context. That does **not** prove that the chunk actually supports the generated claim.

When `ResearchVerifier` is configured, a separate structured model call receives each synthesized claim together with **only the evidence chunks already cited by that claim**. It returns a support verdict and a subset of those cited evidence IDs.

Trusted Python then verifies that:

- every synthesized claim has exactly one verification,
- the verifier cannot invent claim IDs,
- the verifier cannot expand a claim's citation set,
- supported/partial verdicts identify at least one already-cited supporting evidence ID.

Unsupported and contradicted claims remain visible and add the `claim_support_issues` quality flag. They are not silently deleted.

This is a semantic quality-control layer—not formal entailment proof and not independent fact checking.

## Testing

The repository exposes one standard no-cost quality-gate command:

```bash
uv run python scripts/check.py
```

It runs formatting validation, Ruff, mypy, deterministic tests, and the adversarial suite. It does not require credentials or public Internet access.

Real external integrations are opt-in because they require credentials and may incur API charges:

```bash
set -a
source .env
set +a

uv run python scripts/check.py --include-live
```

A separate bounded real-research smoke test exercises the public CLI without using the capability's intentionally generous generic defaults:

```bash
uv run python scripts/research_smoke.py
```

Broad real research commands can consume substantially more pages and LLM context than the smoke profile, so they are treated as demos/benchmarks rather than routine repository health checks.

See [Testing Strategy](docs/testing.md) for the test hierarchy and [Recorded test runs](reports/test-runs/README.md) for publication-ready statistics.

## Result model

A successful `ResearchResult` contains:

- `answer`
- `claims`, each referencing trusted `evidence_ids`
- `claim_verifications`
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
- a `supported` verifier verdict proves real-world truth,
- LLM verification is formal logical entailment,
- all SSRF/parser edge cases have been formally verified,
- application-layer controls replace network/container isolation,
- LLM outputs are deterministic,
- the project is production-certified for sensitive deployments.

The design demonstrates bounded authority, provenance control, verification layers, and testable security properties. The comparative containment benchmark makes those authority-boundary differences reproducible against direct-tool and detector-only baselines.

## Project layout

```text
src/safe_web_research/
  cli.py        standalone CLI
  domain/       strict provider-neutral models
  search/       search abstraction + Brave
  fetch/        DNS/IP policy + bounded SafeFetcher
  extraction/   HTML/text extraction
  llm/          provider abstraction + OpenRouter
  research/     budgets, planning, gathering, synthesis, verification
  security/     suspicious-content observability

tests/
  unit/         deterministic component tests
  integration/  deterministic multi-component tests
  adversarial/  hostile-input security regressions
  benchmark/    deterministic comparative-benchmark regressions
  live/         opt-in real-service tests

fixtures/adversarial/   hostile external-content fixtures
benchmarks/             comparative corpus, runners, methodology/results
reports/test-runs/      reproducible execution statistics
scripts/                development/reporting utilities
docs/                   architecture, threat model, testing, CLI, ADRs
```

## Development principles

1. The model is not an authorization mechanism.
2. Internet-derived content is untrusted data.
3. Trusted code owns network and resource authority.
4. Provider responses are normalized and validated.
5. Citation existence and semantic citation support are separate checks.
6. Security-sensitive behavior should have deterministic regression coverage.
7. Live-provider tests supplement rather than replace deterministic testing.
8. Security detectors and semantic verifiers provide defense in depth; they do not replace containment.
9. Security and quality claims should be backed by committed, reproducible test or benchmark artifacts.

See [CONTRIBUTING.md](CONTRIBUTING.md) before changing security-sensitive code.

## License

Apache License 2.0.

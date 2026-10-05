# Live agent-usage benchmark

This benchmark evaluates a complete **outer agent -> safe-web-research tool -> final answer** loop.
It complements `benchmarks/research_quality/`, which calls `ResearchService` directly.

The benchmark exists to answer integration questions that matter before placing the capability
behind a larger agent harness:

- does the outer model select the intended bounded web capability?
- does a mixed task cause multiple tool calls only when source constraints differ?
- how many Brave searches, fetches, pages, LLM tokens, and Jev judgements are consumed?
- how long until the first research result and until the final answer?
- which part of that time is Brave Search, safe page fetching, inner research LLM inference, Jev,
  outer-agent inference, or extraction/orchestration?
- how much tracked cost belongs to the outer agent versus the research subsystem?
- does the final answer cite URLs that were actually returned by the tool?

## Cases

`cases.json` covers all four profiles exposed by `examples/research_agent/`:

- `official_sources` for domain-restricted official documentation;
- `recent_web` for freshness-constrained research;
- `regional_web` for language/country-constrained research;
- `open_web` for ordinary unrestricted public-web research;
- one mixed case that should use `official_sources` and `recent_web` in separate tool calls.

The checks are deliberately lightweight. They verify routing/profile use, minimum tool/search/source
counts, simple answer anchors, and citations that match tool-returned URLs. They are not a general
semantic quality score. The `open-web-ssrf` case intentionally requires two cited sources because
its task explicitly asks for two independent explanations; a one-source final answer is a real
quality failure rather than an eval threshold to relax. A failed case lists the exact failed checks
instead of only printing `FAIL`.

## Run

```bash
set -a
source .env
set +a

uv run python -m benchmarks.agent_usage --allow-dirty
```

Start with one case when you only want a cheap smoke measurement:

```bash
uv run python -m benchmarks.agent_usage \
  --case-id official-python-taskgroup \
  --allow-dirty
```

The benchmark deliberately separates the outer routing model from the research model. By
default the outer agent uses `openai/gpt-6-luna`; `OPENROUTER_MODEL` only changes the inner
research stack. This prevents an experimental research-model override from silently changing the
structured-output behavior of the agent itself. The default `compact` research profile still runs
the complete planner -> gatherer -> synthesizer -> verifier pipeline, but bounds selected evidence
and model context much more tightly for interactive agent experiments. Use the `full` profile
(`--research-profile full`) to reproduce the earlier generous evidence/token limits.

Start latency measurements with the default research model before overriding it. The full pipeline
can invoke the research model three times per tool call, so a model with high per-call latency can
dominate wall time even when Brave Search and page fetching are fast. To compare models explicitly:

```bash
uv run python -m benchmarks.agent_usage \
  --agent-model openai/gpt-6-luna \
  --research-model openai/gpt-6-luna \
  --allow-dirty

# Cost/latency comparison against another research model:
uv run python -m benchmarks.agent_usage \
  --case-id recent-python-315 \
  --research-model z-ai/glm-5.3-flash \
  --allow-dirty
```

Models/providers can differ substantially in strict structured-output reliability. The benchmark
now records such failures as per-case `ERROR` results and continues with the remaining cases.

### Current exploratory default

`openai/gpt-6-luna` is the current default for both the outer agent and the inner research stack.
This choice is based on local exploratory agent-usage runs, not committed release evidence. On
2026-10-05, a dirty-tree five-case compact-profile run completed in **155.63s** with **$0.020698**
of tracked OpenRouter/Jev cost and passed 4/5 cases. The only failure was `open-web-ssrf` on
`citation_count`: research returned enough sources, but the outer final answer cited fewer than the
two independent sources explicitly required by the task. The agent now preserves claim-to-source
URLs from trusted evidence references and instructs the finalizer to keep multi-source citation
diversity. Rerun the suite after this change before treating 5/5 as measured evidence.

The same exploratory run spent 103.88s inside safe-web-research, of which 89.21s was inner research
LLM time; Brave Search accounted for 7.29s and safe page fetching for 4.30s. This is why model
latency remains a first-class benchmark dimension even when web-provider latency is low.

The compact profile is an example-integration setting, not a change to the package defaults. It uses
a 30k-character selected-evidence ceiling, 2.5k-character extraction chunks, a 30k-character
synthesis payload ceiling, a 60k-character verification ceiling, and a 40k aggregate research input
token budget. The `full` profile preserves the previous example settings for comparison:

```bash
uv run python -m benchmarks.agent_usage \
  --case-id recent-python-315 \
  --research-profile full \
  --allow-dirty
```

Results are written under `reports/agent_usage/local/`. That local directory is ignored by Git on
purpose; these are exploratory measurements, not release evidence.

The run is live and paid/stochastic. `tracked_cost_usd` contains cost reported by successful
OpenRouter chat completions and Jev decisions. If a provider returns an unusable completion and
raises before usage is exposed, that failed request is not included, so an error run is a
lower-bound cost. Brave Search monetary cost is not exposed by the current provider contract, so
the benchmark records Brave request count separately.

Each case is printed as it starts and finishes. A provider failure no longer aborts the five-case
suite or discards earlier measurements; it is written into the Markdown/JSON report with its error
type and message. A second request for an already-complete identical evidence scope is suppressed,
because one `safe_web_research` invocation already performs planning, search, page fetching,
synthesis, and verification. This avoids measuring an accidental duplicate full research cycle as
if it were useful agent work.

For an overhead ablation, rerun the same case with semantic verification and Jev observation
disabled. This changes the safety/quality profile, so use it only to understand where latency and
provider cost are coming from:

```bash
uv run python -m benchmarks.agent_usage \
  --case-id official-python-taskgroup \
  --no-verify \
  --content-judgement off \
  --allow-dirty
```

### Failure and latency diagnostics

The report distinguishes outer-agent/provider errors from search-provider errors and lists the exact
assertions behind a normal `FAIL`. Every actual Brave attempt is traced with its generated query
constraints, latency, result count, and bounded error message. It also records safe-fetch latency,
planner/synthesis/verification model latency, and Jev latency. Because Jev judgements for one
research operation run concurrently, the timing report uses the slowest judgement in that operation
as the approximate Jev critical path instead of incorrectly summing concurrent calls. A failed live
case is recorded and the suite continues with the next case.

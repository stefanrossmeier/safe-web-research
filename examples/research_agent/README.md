# Local bounded research agent example

This example is intentionally shaped like an upstream harness integration rather than a direct
`ResearchService` demo. An **outer agent** receives a user task, decides whether and how to call
one bounded tool, and then writes a final answer from the returned evidence.

The model does **not** receive Brave Search, arbitrary HTTP, browser, shell, filesystem, or MCP
tools. Its only external capability is `safe_web_research`, implemented by trusted Python code.
That wrapper maps four explicit profiles to `ResearchRequest` constraints. The profiles are an
example harness contract, not a replacement for every `ResearchRequest` field:

| Capability | Intended use | Trusted constraint |
| --- | --- | --- |
| `open_web` | General research | No domain/freshness/locale constraint |
| `official_sources` | Official docs or named source set | Requires 1-5 allowed domains |
| `recent_web` | Time-sensitive research | Requires a 1-90 day freshness window |
| `regional_web` | Local/language-specific research | Requires language and country |

This is close to the intended Safeplane use: the agent chooses a declared capability, while the
harness owns validation, budgets, provider credentials, and the real tool invocation.

## Run locally on a MacBook

Use the repository's normal environment first:

```bash
uv sync
cp .env.example .env
# fill BRAVE_API_KEY and OPENROUTER_API_KEY
set -a
source .env
set +a
```

Run one task:

```bash
uv run python -m examples.research_agent \
  "Compare what the official Python docs say changed in Python 3.15 with recent public-web commentary. Cite sources."
```

The outer routing model and the inner research model are intentionally configured separately.
`OPENROUTER_AGENT_MODEL` controls the small structured routing decisions; `OPENROUTER_MODEL`
continues to control the research planner/synthesizer/verifier. If `OPENROUTER_AGENT_MODEL` is
unset, the example uses the repository default `openai/gpt-6-luna`. The example also defaults to a
`compact` research profile: it keeps planner, synthesis, verification, safe fetch, provenance, and
Jev observability, while bounding selected evidence/model context for interactive use. Use
`--research-profile full` to reproduce the earlier larger limits.

Start with the defaults when measuring latency. A full tool invocation can call the inner research
model three times, so a slow research model can dominate end-to-end time even when web search is
fast. Override the research model only when you intentionally want a model comparison:

```bash
OPENROUTER_AGENT_MODEL=openai/gpt-6-luna \
OPENROUTER_MODEL=openai/gpt-6-luna \
uv run python -m examples.research_agent \
  "Using only docs.python.org, explain asyncio.TaskGroup failure behavior. Cite the source."

# Preserve the previous, more generous example evidence/token limits:
uv run python -m examples.research_agent \
  --research-profile full \
  "Using only docs.python.org, explain asyncio.TaskGroup failure behavior. Cite the source."
```

The routing decision is deliberately tiny and the final prose answer is generated in a separate
plain-text call. This keeps strict structured output away from long answers and bounds the
agent-facing tool observation before it is put back into model context. Claim observations retain a
bounded list of source URLs resolved from the claim's evidence references (or verifier-supported
evidence when available), so the outer finalizer does not lose provenance when it rewrites the
inner research answer. Comparative/multi-source tasks explicitly ask the finalizer to cite multiple
distinct supporting URLs when the evidence contains them. One successful research
call is also treated as sufficient for the same evidence scope: if the outer model immediately asks
for another `recent_web`/`official_sources`/etc. call with identical constraints, the harness
finalizes from the evidence it already has instead of paying for the complete research pipeline a
second time. A genuinely different scope (for example official sources followed by recent public
web) is still allowed.

Save the full trace:

```bash
uv run python -m examples.research_agent \
  "Find recent Python 3.15 release information and cite sources." \
  --output /tmp/safe-web-research-agent.json
```

The human-readable output reports:

- end-to-end wall time and time to the first completed research result;
- outer-agent tokens and OpenRouter-reported cost;
- inner `safe-web-research` tokens and OpenRouter/Jev-reported cost;
- Brave search count, fetch attempts, pages fetched, and Jev judgement calls;
- every capability selected by the agent and per-tool-call latency/cost;
- separate latency for Brave Search, safe page fetches, inner research LLM calls, Jev's approximate
  critical path, and the outer agent;
- how many redundant same-scope research calls the harness prevented.

`tracked_cost_usd` does **not** include Brave subscription/query charges because the current
search-provider contract reports request counts, not monetary search cost. If a provider returns
an unusable completion and the adapter raises before it can expose usage, the failed request is
also not measurable; error runs therefore report a lower-bound tracked cost.

## Run the eval suite

The live evals under `benchmarks/agent_usage/` test all four profiles plus one mixed task that
should make the agent use two different profiles in a single run:

```bash
uv run python -m benchmarks.agent_usage --allow-dirty
```

They are deliberately live and stochastic. They are useful for answering practical questions
before wiring this into a larger harness: Does the agent select the right bounded capability?
How many searches/pages does the nested research perform? How long until a result? How much of
the cost sits in the outer loop versus the research tool? Does the final answer cite sources the
tool actually returned? The JSON benchmark artifact keeps the compact full agent trace for each
case so routing, model decisions, sources, latency, and usage can be inspected after the run.

### Search diagnostics

Each tool call records actual search-provider attempts (query constraints, latency, result count,
and bounded error details), individual safe-fetch attempts, inner planner/synthesizer/verifier calls,
and Jev judgement calls. This makes a slow Brave request distinguishable from slow page fetching,
model inference, or semantic judgement without changing the production APIs.

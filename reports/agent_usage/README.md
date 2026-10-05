# Agent-usage reports

Local exploratory output from `python -m benchmarks.agent_usage` goes under `local/` and is ignored
by Git. The benchmark records end-to-end agent latency, capability use, search/fetch/page counts,
token usage, Jev calls, citations, provider-reported model/Jev cost, and per-case provider errors.
A live-provider failure is retained in the report and does not abort the remaining suite.

These measurements are intentionally separate from the committed research-quality and security
benchmark evidence. Promote a result family into release evidence only after its methodology and
recording policy are explicitly reviewed.

Live reports also record bounded per-search, per-fetch, inner-research-LLM, and Jev diagnostics.
They show exact failed eval checks and separate Brave Search time from the much larger
`safe-web-research` operation, so a slow provider request is not confused with fetching, inference,
semantic judgement, or orchestration overhead.

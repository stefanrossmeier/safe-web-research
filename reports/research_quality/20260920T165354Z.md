# Live research-quality matrix

- Timestamp (UTC): `2026-09-20T16:53:54.588217+00:00`
- Git commit: `66cec8f74530`
- Git dirty: `False`
- Model: `z-ai/glm-5.3-flash`
- Case file: `benchmarks/research-quality/cases.json`

## Aggregate

- Passed cases: **5/5**
- Total input tokens: **107851**
- Total output tokens: **6652**
- Total provider cost: **$0.019815**
- Total fetch attempts: **13**
- Total pages fetched: **13**
- Total wall time: **126.64s**

## Cases

| Case | Category | Pass | Terms | Claims verified | Support | Pages | Input | Output | Cost | Seconds | Hard-limit flags |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| python-315-utf8 | language-documentation | yes | 3/3 | 6/6 | 6 supported, 0 partial, 0 unsupported, 0 contradicted | 3 | 23714 | 1027 | $0.004071 | 26.18 | — |
| httpx-timeouts | library-documentation | yes | 4/4 | 6/6 | 6 supported, 0 partial, 0 unsupported, 0 contradicted | 3 | 14652 | 881 | $0.002638 | 10.03 | — |
| pydantic-strict-mode | library-documentation | yes | 2/2 | 7/7 | 7 supported, 0 partial, 0 unsupported, 0 contradicted | 3 | 13765 | 1462 | $0.002796 | 52.12 | — |
| owasp-ssrf-guidance | security-guidance | yes | 3/3 | 8/8 | 8 supported, 0 partial, 0 unsupported, 0 contradicted | 2 | 22413 | 1696 | $0.004210 | 15.05 | — |
| python-taskgroup | api-documentation | yes | 3/3 | 10/10 | 10 supported, 0 partial, 0 unsupported, 0 contradicted | 2 | 33307 | 1586 | $0.006100 | 23.25 | — |

## Interpretation

This is a live provider/network quality matrix, not a security benchmark. Search results, provider routing, latency, token usage, and cost may vary.
A case passes only when expected anchor terms are present, every synthesized claim is verified, no claim is unsupported/contradicted, and no hard research ceiling or synthesis truncation flag is hit. Partial support is allowed.
The expected terms are lightweight regression anchors, not a complete semantic answer-quality score. Human review remains necessary for publication claims.

# Architecture

## Design Principles

1. Internet-derived content is always untrusted.
2. The LLM is not a security boundary.
3. Trusted Python code owns authority.
4. Models propose structured decisions; trusted code executes permitted operations.
5. Search, fetching, extraction, LLM inference, and orchestration are separate concerns.
6. External providers are accessed through internal interfaces.
7. Research operations have hard resource budgets.
8. Significant claims retain source provenance.
9. The core implementation is deployment- and protocol-independent.
10. Safeplane is a future consumer, not an internal dependency.

## Target Architecture

```text
                    ResearchService
                          |
             +------------+------------+
             |            |            |
             v            v            v
       Orchestrator  SearchProvider  LLMProvider
             |            |            |
             |       Brave / Fake  OpenRouter / Fake
             |
             v
        SafeFetcher
             |
             v
         Extractor
             |
             v
         Evidence
             |
             v
     Claims / Verification
             |
             v
       ResearchResult
```

## External Adapters

The core ResearchService should eventually be exposed through:

- Python
- CLI
- HTTP/REST
- MCP

All adapters use the same core implementation.

## Safeplane Integration

Safeplane integration is intentionally deferred.

Safeplane should eventually receive a high-level `research` capability rather than low-level arbitrary `search` or `fetch` capabilities.

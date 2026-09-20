# ADR 0007: Decode HTTP Compression Explicitly and Bound Decompressed Content

## Status

Accepted

## Context

Many public sites serve gzip-encoded text. Rejecting all compression hurts web compatibility, but enabling transparent HTTP-client decompression can make byte accounting ambiguous and expose decompression-amplification/resource-exhaustion risk.

Malformed, truncated, or concatenated compressed streams can also create parser ambiguity.

## Decision

`SafeFetcher` will advertise only `gzip, identity` and consume the raw response stream itself.

For gzip responses:

- compressed bytes are bounded;
- decompression is incremental;
- the per-page byte ceiling applies to decompressed output;
- output exceeding the ceiling fails immediately;
- malformed or truncated streams fail closed;
- concatenated gzip members are rejected;
- unsupported content encodings are rejected.

The resulting bounded decompressed body is what downstream extraction receives and what successful-page byte accounting records.

## Consequences

The project gains compatibility with common gzip web responses without delegating resource policy to implicit client behavior.

The policy is intentionally narrower than a general browser: encodings such as Brotli are currently unsupported and fail closed until implemented with equivalent explicit bounds/tests.

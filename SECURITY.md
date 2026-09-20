# Security Policy

## Project status

`safe-web-research` is a pre-1.0 reference implementation. It makes important security boundaries explicit and testable, but it has not undergone an independent security audit.

## Reporting a vulnerability

Please report suspected vulnerabilities privately.

Prefer GitHub private vulnerability reporting / a private security advisory when available. Do not publish credentials, exploit details, or sensitive reproduction data in a public issue.

A useful report includes:

- affected commit/version;
- threat scenario;
- minimal reproduction;
- expected security invariant;
- observed behavior;
- whether real credentials/external systems were involved.

## Security invariants

- Fetched web content does not receive direct network, shell, filesystem, secret, or arbitrary-action authority.
- Planner/synthesizer/verifier models receive no arbitrary tools.
- Fetch targets and redirects are validated independently of model intent.
- Non-global network destinations are rejected and connections are pinned to validated addresses.
- Compressed response handling is explicitly bounded on decompressed output.
- Canonical source/evidence/claim identity is owned by trusted code.
- Model references are accepted only when they resolve to the supplied trusted context.
- Structured LLM output is schema-validated locally.
- Hard resource budgets are enforced by trusted code.
- Suspicious-content detection is diagnostic only and is not required for containment.

A violation of one of these invariants is security-relevant even if the final natural-language answer looks harmless.

## Secrets

Never commit:

- `.env`;
- Brave/OpenRouter credentials;
- production URLs containing secrets;
- captured authorization headers/tokens.

Live tests and the CLI read credentials from environment variables. The CLI intentionally does not accept API keys as command-line options.

## Threats explicitly considered

The current [Threat Model](docs/threat-model.md) covers indirect prompt injection, excessive agency/tool abuse, SSRF/cloud metadata, DNS rebinding, compressed-content amplification, secret exfiltration, provenance poisoning, unsupported claims, denial of wallet/resource exhaustion, malformed provider responses, source misinformation, and the CLI authority surface.

## Important non-guarantees

The project does not guarantee:

- factual correctness of sources/answers;
- perfect prompt-injection detection;
- formal semantic entailment or objective truth;
- protection from a compromised host/Python runtime;
- deployment-level egress/sandbox isolation;
- third-party provider availability/security;
- suitability for high-impact autonomous actions.

The current architecture intentionally exposes no consequential external-action tools.

## Testing security changes

Run the standard no-cost gate:

```bash
uv run python scripts/check.py
```

For the deterministic compromised-model benchmark (no API keys/network):

```bash
uv run python -m benchmarks.security
```

Live tests are useful before release but do not replace deterministic security regression coverage.

# Security Policy

## Project status

`safe-web-research` is currently a pre-1.0 reference implementation. It is designed to make important security boundaries explicit and testable, but it has not undergone an independent security audit.

## Reporting a vulnerability

Please report suspected vulnerabilities privately.

Prefer GitHub private vulnerability reporting / a private security advisory when available. Do not publish credentials, exploit details, or sensitive reproduction data in a public issue.

A useful report includes:

- affected commit or version,
- threat scenario,
- minimal reproduction,
- expected security invariant,
- observed behavior,
- whether real credentials or external systems were involved.

## Security invariants

The project is designed around these invariants:

- Fetched web content does not receive direct network, shell, filesystem, or arbitrary tool authority.
- The research synthesizer has no tools.
- Fetch targets are validated independently of LLM decisions.
- Redirect targets are revalidated.
- Non-global IP destinations are rejected.
- Claims returned by synthesis may reference only evidence IDs created by trusted code.
- Structured LLM output is schema-validated locally.
- Resource budgets are enforced by trusted code.
- Suspicious-content detection is diagnostic only and is not required for containment.

A violation of one of these invariants is security-relevant even if the final natural-language answer looks harmless.

## Secrets

Never commit:

- `.env`,
- Brave API keys,
- OpenRouter API keys,
- provider credentials,
- production URLs containing secrets,
- captured headers containing authorization tokens.

Live tests read credentials from environment variables and are excluded from deterministic test runs.

## Threats explicitly considered

The current threat model covers:

- indirect prompt injection from web content,
- prompt/role impersonation inside evidence,
- secret-exfiltration instructions,
- SSRF,
- DNS rebinding / validation-to-connection gaps,
- redirect-based SSRF bypasses,
- cloud metadata access,
- fabricated evidence or citations,
- malicious structured LLM output,
- unbounded resource consumption,
- provider failures and malformed responses.

See `docs/threat-model.md`.

## Important non-guarantees

The project does not guarantee:

- factual correctness of web sources or answers,
- perfect prompt-injection detection,
- semantic entailment between every claim and cited chunk,
- protection against a compromised host or Python runtime,
- protection equivalent to deployment-level egress filtering or sandboxing,
- availability of third-party providers,
- suitability for high-impact autonomous actions.

The V1 architecture intentionally exposes no consequential external-action tools.

## Testing security changes

Changes to fetching, DNS policy, redirects, extraction, model prompts, structured schemas, citations, budgets, or external-content handling should include an adversarial regression test.

Run:

```bash
uv run ruff check .
uv run mypy src
uv run pytest -m "not live" -q
uv run pytest -m adversarial -v
```

Live tests are useful before release but are not a substitute for deterministic security tests.

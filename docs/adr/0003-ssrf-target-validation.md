# ADR 0003: SSRF Target Validation and Address Pinning

## Status

Accepted

## Context

The research service fetches URLs derived from untrusted Internet search results.

URL validation alone is insufficient because a hostname may resolve to loopback,
private, link-local, shared, reserved, or otherwise non-public addresses.

A hostname may also change its DNS response between validation and connection.

Redirects create the same problem for every subsequent target.

## Decision

The fetch layer will:

1. Accept only HTTP and HTTPS.
2. Reject URL user information.
3. Reject non-standard web ports in V1.
4. Reject internal-style and single-label hostnames.
5. Resolve all A and AAAA addresses before connection.
6. Require every resolved address to be globally reachable.
7. Re-run the complete validation process for every redirect target.
8. Disable automatic redirect following.
9. Connect to an address that was actually validated rather than allowing
   the HTTP client to independently resolve the hostname again.
10. Preserve the original hostname for the HTTP Host header and TLS SNI.

## Consequences

The policy is intentionally conservative and may reject unusual but legitimate
public websites.

Those cases can be evaluated later and relaxed deliberately.

The actual HTTP connection layer must preserve the validated-address binding;
performing validation and then allowing an HTTP library to perform a second
independent DNS lookup would violate this ADR.

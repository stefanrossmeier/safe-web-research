# ADR 0003: SSRF Target Validation and Address Pinning

## Status

Accepted

## Context

The research service fetches URLs derived from untrusted Internet search results.

URL syntax validation alone is insufficient because a hostname may resolve to loopback, private, link-local, shared, reserved, or otherwise non-public addresses. A hostname may also change its DNS response between validation and connection. Redirects create the same problem for every subsequent target.

## Decision

The fetch layer will:

1. accept only HTTP and HTTPS;
2. reject URL user information;
3. accept only standard web ports 80/443;
4. reject internal-style and single-label hostnames;
5. resolve all A/AAAA addresses before connection;
6. require every resolved address to be globally reachable;
7. reject mixed public/non-public resolution sets;
8. rerun complete validation for every redirect target;
9. disable automatic redirect following;
10. connect to an address that was actually validated rather than allowing the HTTP client to independently resolve the hostname again;
11. preserve the original hostname for HTTP `Host` and TLS SNI;
12. ignore environment proxy configuration for this fetch path.

## Consequences

The policy is intentionally conservative and may reject unusual but legitimate public sites. Relaxations must be deliberate and regression-tested.

The HTTP connection layer is part of the security decision: validating DNS and then allowing an independent second resolution would violate this ADR.

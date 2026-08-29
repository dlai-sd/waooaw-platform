# ADR-048: Public OIDC Identity Edge

**Status:** Accepted - Founder approval recorded 2026-08-29
**Date:** 2026-08-29
**Office:** Chief Enterprise Architect (INST-004)
**Work Contract:** WC-077 focused architecture remediation
**Constitutional basis:** C-032, C-059, C-063, C-067, C-100; ADR-008, ADR-010, ADR-012, ADR-014

## Context

Keycloak is WAOOAW's credential authority and federation broker. The accepted Azure deployment
topology keeps Keycloak private and requires one pinned public identity edge that exposes only the
OIDC paths needed by web and future mobile clients. Azure Container Apps ingress supplies transport
ingress and TLS but does not provide the required Keycloak path allowlist or deny its administration,
management, metrics, and arbitrary proxy surfaces.

The identity edge is not an authentication authority, API facade, session store, token transformer,
or exact-six application member. Its only purpose is to enforce the narrow public OIDC boundary in
front of private Keycloak.

## Decision

Use **NGINX Open Source 1.27.5 Alpine** as the stateless public OIDC identity edge.

1. The image is a third-party runtime dependency, pinned by OCI digest after repository security and
   compatibility checks. A mutable tag is never deployment authority.
2. Azure Container Apps exposes the edge at the environment's public identity hostname. Keycloak has
   internal ingress only and accepts identity traffic from the edge through the private environment.
3. The edge uses a deny-by-default, version-controlled route policy. It permits only the exact OIDC
   discovery, authorization, token, logout, broker-callback, login-action, and required static-resource
   paths specified by the Solution Architect. It denies Keycloak administration, management, health,
   metrics, debug, unlisted realms, and arbitrary proxy paths.
4. The edge forwards requests without reading, storing, rewriting, minting, introspecting, or logging
   credentials, authorization codes, cookies, or tokens. Redacted access logs contain correlation,
   route class, status, latency, environment, and dependency version only.
5. The edge adds no application authorization. Business Platform remains the sole public business API
   and independently validates Keycloak tokens and customer authority.
6. The edge image digest and route-policy digest are recorded in the signed dependency manifest bound
   to the exact-six release tuple. Keycloak image digest and normalized realm-config digest are recorded
   in the same manifest. Neither dependency becomes an exact-six member.
7. Edge and Keycloak upgrades are compatibility-qualified together. Rollback restores the immediately
   previous qualified edge-image/policy and Keycloak-image/realm tuple; promotion never rebuilds them.
8. Demo, UAT, and Production use the same image and policy schema with environment-specific hostnames,
   realm/client values, certificates, and secret references. Production remains dark until separately
   authorized.

## Alternatives Considered

| Alternative | Disposition |
|---|---|
| Expose Keycloak directly through Container Apps ingress | Rejected: exposes a broader Keycloak surface and cannot enforce the required path contract |
| Azure Application Gateway or Front Door for Demo/UAT | Rejected: adds cost and topology beyond the accepted non-Production boundary |
| Implement a custom proxy in Business Platform or Web | Rejected: creates security-sensitive proxy code and mixes credential ingress with application responsibilities |
| Caddy or Envoy | Rejected for this bounded edge: both can implement the policy, but NGINX has the smallest required feature and operational surface for static path mediation |

## Consequences

- `architecture/reference/components/identity-edge.md` defines the exact route, header, timeout,
  body-size, cache, redaction, health, telemetry, failure, and evidence contract.
- `architecture/reference/pipeline/identity-dependency-manifest.md` defines immutable dependency,
  configuration, compatibility, promotion, and non-destructive rollback binding.
- Platform IT must package only version-controlled configuration around the pinned upstream image; it
  must not add authentication logic or provider-specific business behavior.
- Security validation must prove every allowed route and representative denied route, header and log
  redaction, request-size limits, timeout behavior, private Keycloak reachability, and public Keycloak
  unreachability.
- NGINX is portable across Docker and Azure Container Apps, preserving ADR-010's escape hatch.

## Authorization Boundary

The Founder accepted this ADR on 2026-08-29 and separately authorized WC-077 implementation for the
current session. That authority permits repository source, test, image, workflow, and infrastructure
changes required by WC-077. It does not activate an externally blocked provider or authorize cloud,
DNS, environment deployment, customer traffic, UAT, or Production mutation; those gates remain
independent.

## Author Review

**Result:** PASS - accepted architecture.

The decision was checked against the private-Keycloak topology, provider-broker boundary, exact-six
membership, immutable promotion, secret isolation, cost, portability, failure behavior, and rollback.
No unresolved Enterprise Architecture question remains inside the customer identity-edge scope.
# Public OIDC Identity Edge Contract

**Document type:** Proposed component and integration contract
**Owning office:** INST-005 - Solution Architect
**Enterprise decision:** ADR-048, Proposed - Founder acceptance required
**Work Contract:** WC-077 focused architecture remediation
**Status:** FOUNDER REVIEW CANDIDATE; NOT IMPLEMENTATION AUTHORITY

## 1. Purpose and boundary

The Identity Edge is a stateless NGINX Open Source 1.27.5 Alpine dependency that exposes the minimum
customer OIDC browser/mobile surface while Keycloak remains private. It does not authenticate users,
validate or transform tokens, terminate application sessions, proxy Business Platform, store state,
or implement provider-specific behavior.

It is a pinned dependency-manifest member and is not one of the exact-six application images. This
contract becomes binding only if the Founder accepts ADR-048.

## 2. Public route policy

Only the configured customer realm is accepted. Realm and broker aliases are exact configured values,
not arbitrary path captures. The public route policy permits:

| Route class | Exact path family | Methods | Purpose |
|---|---|---|---|
| Discovery | `/realms/{customer-realm}/.well-known/openid-configuration` | `GET`, `HEAD` | OIDC discovery |
| Keys | `/realms/{customer-realm}/protocol/openid-connect/certs` | `GET`, `HEAD` | Public signing keys |
| Authorization | `/realms/{customer-realm}/protocol/openid-connect/auth` | `GET`, `POST` | Authorization request and form continuation |
| Token | `/realms/{customer-realm}/protocol/openid-connect/token` | `POST` | Authorization-code/refresh exchange by approved clients |
| Logout | `/realms/{customer-realm}/protocol/openid-connect/logout` | `GET`, `POST` | RP-initiated session logout |
| Broker | `/realms/{customer-realm}/broker/{approved-alias}/login` and `/endpoint` | `GET`, `POST` | Approved broker redirect/callback only |
| Login actions | `/realms/{customer-realm}/login-actions/*` | `GET`, `POST` | Keycloak-owned authentication actions |
| Static resources | `/resources/*` | `GET`, `HEAD` | Keycloak theme assets only |
| Edge health | `/healthz` | `GET` | Edge-local liveness; never proxies Keycloak health |

Every other route and method returns a uniform edge `404` without upstream contact. The deny set
includes `/admin`, `/management`, `/metrics`, Keycloak health, root/admin console, other realms,
userinfo, introspection, device authorization, dynamic client registration, account console, debug,
and arbitrary proxy paths. A newly required OIDC path is a reviewed contract change, never a runtime
wildcard.

## 3. Request and response controls

- Preserve method, request body, query, host intent, and Keycloak status; do not rewrite tokens,
  cookies, codes, state, nonce, PKCE, redirect URI, issuer, or error fields.
- Set the private upstream host explicitly. Forward a sanitized request ID and standard forwarding
  metadata; discard inbound forwarding headers before constructing trusted values.
- Forward `Authorization` only on the token route. Never forward proxy credentials supplied by a
  client. Strip hop-by-hop and unapproved headers.
- Do not cache authorization, token, logout, broker, login-action, authenticated HTML, or errors.
  Discovery, JWKS, and immutable static assets may use bounded cache headers compatible with Keycloak
  key rotation; the edge itself remains stateless.
- Browser/form routes accept at most 64 KiB and token requests at most 16 KiB. Static-resource
  responses are limited by the pinned Keycloak theme qualification. Oversize requests return `413`
  without upstream contact.
- Connect timeout is 5 seconds, response-header timeout 30 seconds, and total request timeout 60
  seconds. Timeout or private-upstream failure returns a generic `503`; no alternate issuer or bypass
  is attempted.
- TLS is required outside local Docker. HSTS and secure-cookie behavior are environment-reviewed;
  permissive CORS is prohibited. OIDC endpoints use only exact approved origins and redirect URIs as
  enforced by Keycloak client configuration.

## 4. Privacy and observability

Access and error logs may contain timestamp, environment, edge version, route class, request/correlation
ID, method, status, response bytes, and latency. They must not contain query strings, request or response
bodies, cookies, authorization headers, client secrets, codes, tokens, state, nonce, PKCE values,
provider payloads, email, mobile, subject, tenant, realm credentials, or full upstream URLs.

Metrics are aggregate route-class counts, status classes, latency, connection failure, timeout, and
request rejection. Metrics and Keycloak management surfaces remain private. Trace attributes follow
the same redaction rules and never propagate user-supplied trace identity without validation.

## 5. Configuration and secrets

Demo, UAT, and Production use the same reviewed policy schema and pinned edge image. Environment inputs
are limited to public identity hostname, private Keycloak origin, exact customer realm, approved broker
aliases, trusted private network/forwarding settings, TLS reference, telemetry destination, and policy
digest. No provider client secret belongs in the edge. Unknown values, wildcard realms/aliases/origins,
HTTP outside local Docker, public Keycloak upstream, mutable image reference, or policy-digest mismatch
fails startup/readiness.

The route policy is generated from reviewed structured configuration and is immutable for a deployed
revision. Runtime administrative mutation and remote include/download are prohibited.

## 6. Failure and rollback

If the edge is unavailable, public login and refresh fail closed while existing Business Platform
sessions continue according to their own validity. If Keycloak is unavailable, the edge returns a
generic `503`; it does not cache a successful token response or redirect to another environment.
Denied paths never reach Keycloak.

Promotion references the same signed edge digest and route-policy digest used in Demo. Rollback selects
the immediately previous qualified edge/policy plus Keycloak/realm tuple from the signed dependency
manifest. No rebuild, mutable retag, policy substitution, cross-environment secret copy, or issuer
change is allowed during promotion or rollback.

## 7. Required evidence

1. Every allowed method/path reaches the intended private Keycloak route; representative path encoding,
   traversal, duplicate-slash, case, other-realm, admin, management, metrics, health, and arbitrary
   paths are denied without upstream contact.
2. Header tests prove trusted forwarding reconstruction, token-route-only authorization forwarding,
   hop-by-hop stripping, exact host behavior, and no open proxy.
3. Body, timeout, cache, TLS, CORS, and fail-closed behavior pass in Docker with the pinned images.
4. Captured logs, metrics, and traces contain none of the prohibited identity or credential values.
5. Public probes cannot reach Keycloak directly in Demo; private edge-to-Keycloak connectivity works.
6. Edge image, policy, SBOM, provenance, vulnerability result, and compatibility result are digest-bound
   in the dependency manifest for Demo, UAT, Production, and rollback.

## 8. Author review

**Result:** PASS as a proposed Solution Architecture contract. It is conditional on Founder acceptance
of ADR-048 and grants no implementation, cloud, DNS, provider, deployment, or traffic authority.

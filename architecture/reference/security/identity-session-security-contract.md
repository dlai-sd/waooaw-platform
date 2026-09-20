# Identity Session Security Contract

**Authority:** WC-103; Founder-requested Security Architect one-pass edit review, 2026-09-20
**Status:** PROPOSED FOR FOUNDER REVIEW - IMPLEMENTATION NOT AUTHORIZED
**Constitutional basis:** C-001, C-002, C-023, C-026, C-048, C-063, C-100; ADR-003, ADR-008, ADR-009

## Security Outcomes

1. Authentication uses Keycloak-brokered authorization code flow with PKCE, server-held state and
   nonce, exact issuer/audience/JWKS validation and exact allowlisted redirect origins.
2. Authentication success rotates the application session identifier. Privilege, assurance, account
   and tenant changes rotate it again; the previous identifier is invalid immediately.
3. Explicit logout invalidates the server session before browser cleanup, invokes Keycloak
   RP-initiated logout, and returns only to an exact allowlisted public origin.
4. After logout, passive navigation, refresh, history restoration, service-worker response and
   background OIDC activity cannot establish a session. A new session requires an explicit customer
   command; social login requires account selection.
5. Revoke-one and revoke-all are authenticated, CSRF-protected, replay-safe operations. The current
   session may revoke itself. Revocation wins every race with refresh or callback completion.
6. Access-token expiry, refresh rotation/reuse, account disablement, membership removal, assurance
   downgrade and session revocation fail closed at every enabled receiver.

## Browser And Provider Boundary

Provider authorization pages use only provider-supported top-level redirect or popup behavior; they
must not be embedded in a WAOOAW iframe. Popup-blocked behavior falls back to a top-level redirect
without losing server-held intent. WAOOAW does not terminate unrelated Google, Facebook or Apple
sessions. It terminates WAOOAW and Keycloak state and requests provider account selection on the next
explicit launch.

Cookies are `Secure`, `HttpOnly`, host-only where practicable, and use the strictest compatible
`SameSite` value. Authenticated HTML, RSC, identity responses and session-bearing responses use
`Cache-Control: no-store`. Logout expires every application cookie variant and clears WAOOAW-owned
cache/storage; broad `Clear-Site-Data` may be used only after proving it does not erase retained public
accessibility, locale or other explicitly preserved state unexpectedly.

## Abuse And Privacy Controls

Rate limits apply to authentication starts, callback failures, registration, email challenges,
recovery, linking and revocation using privacy-safe keyed dimensions. Existing/non-existing accounts
retain indistinguishable response shape and timing class. Provider availability fails closed.

Forensic events contain no password, OTP, authorization code, token, PKCE material, raw provider
subject, raw email/mobile, tenant/resource ID, URI/query, referrer or raw user agent. Security may
retain a rotating keyed network prefix and normalized device/risk class only when the key, retention,
access purpose and DPDPA notice are approved; otherwise those fields are absent. Such values never
become identity, authorization or cross-tenant correlation keys.

## Security Acceptance

- OAuth mix-up, state/nonce replay, PKCE downgrade, callback injection and open redirect tests deny.
- Session fixation and old-cookie reuse deny after login, assurance change and account switch.
- Logout-versus-refresh and revoke-versus-callback races converge on revoked/unauthenticated state.
- Cross-site logout/revocation, forged session IDs and cached protected-page restoration deny.
- Provider cancellation/failure preserves no partial account or usable session.
- Secret/PII scans cover structured logs, database events, traces, screenshots and CI artifacts.

Any failure blocks the affected provider or release. Local or synthetic tests do not establish real
provider, deployed-origin or Production acceptance.
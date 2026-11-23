# ADR-055 - Synthetic Acceptance Tenants And Evidence

**Status:** PROPOSED - awaiting Founder acceptance
**Date:** 2026-11-23
**Decision owner:** Enterprise Architecture (INST-004)
**Authorization:** Founder assignment in the current conversation, 2026-11-23 (architecture package only; no implementation)
**Work Contract:** WC-157
**Constitutional basis:** C-023, C-027, C-049, C-063, C-065, C-066
**Capabilities:** 6.2 Isolate Tenant Data; 6.3 Record Constitutional Evidence; 6.5 Bill Customers with Pro-Rata Precision
**Drivers:** AD-002, AD-003, AD-004, AD-008, AD-009
**Preserved decisions:** ADR-003, ADR-009, ADR-044, ADR-046, ADR-053
**Companion:** ADR-054 (customer journey acceptance)

## Context

The Founder requires acceptance data to be throwaway. Constitutional evidence is append-only
(C-027; PostgreSQL rules forbid UPDATE and DELETE on the constitutional schema for every user), so
"throwaway" cannot mean deletion of evidence.
Trial entitlement is one per customer per agent type and version, so a reused customer can trial once;
a faithful journey run therefore needs a fresh customer each time. Customers register through Google or
Facebook identity brokering with email challenges, which a test cannot complete, and tenant authority comes
only from the verified `(iss, sub)` membership (ADR-003), never from a caller-supplied value.

## Decision

1. **Run-scoped synthetic customers.** Each acceptance run provisions two synthetic customers (A, the
   actor; B, the isolation probe) in the target environment's real Keycloak realm (`waooaw`), as local
   users with a generated password and a generated one-time-password credential so the real login form
   and the step-up flow both work, and a verified email on a reserved synthetic email domain (registration
   requires a verified email). Credentials are generated per run, held only in memory, and never
   printed. Both users are removed from Keycloak when the run ends. Google-brokered first login is not
   exercised and is reported `NOT-COVERED`.
2. **Provisioning identity (decided).** A dedicated Keycloak client `waooaw-acceptance-provisioner` holds
   the realm-management `manage-users` role, the same role pattern already accepted for the
   `keycloak-lifecycle-writer-client` (WC-123). Keycloak fine-grained admin permissions v1 is a preview
   feature in the deployed Keycloak 25 line and is not adopted. Because `manage-users` is realm-wide,
   these compensating controls are mandatory: (a) the client secret exists only in the environment's
   Key Vault under `acceptance-keycloak-provisioner-client-secret` and is readable only by the acceptance
   identity; (b) the harness creates users only with the reserved synthetic username prefix and the
   `synthetic` group, and refuses to read, change or delete any other user (guarded by a test); (c) a
   Keycloak admin-event check after each run fails the run if the client touched any user outside the
   synthetic prefix; (d) the client exists only in Demo and UAT; (e) rotation follows the 90-day
   versioned-overlap class used for the lifecycle writer. The Founder accepts this residual risk for Demo
   and UAT by accepting this ADR.
3. **Same code paths.** A synthetic tenant uses the same registration, entitlement, billing, evidence and
   authority code as any customer. The marker never skips a control, so the run proves real behaviour
   (C-023).
4. **The marker reduces side effects only.** The marker is a server-side registry of synthetic subjects
   (Keycloak `sub` plus run identifier) held by Business Platform and written only through an internal
   route that accepts a Keycloak token carrying a dedicated `acceptance-provisioner` realm role, the same
   validation pattern as the existing `pricing_admin` role routes. The role is never assignable to
   customers, and the route is default-off through a feature setting that exists only in Demo and UAT
   (settings policy S5, S6). A tenant created at first login by a registered subject inherits the marker.
   The marker is not a token claim and is never derived from customer-controlled input (ADR-003:
   membership still comes only from the verified `(iss, sub)`). It never grants authority and is honoured
   only to (a) exclude the tenant from business metrics, revenue and
   customer-facing aggregates, (b) suppress delivery to any recipient other than a registered sandbox
   recipient, and (c) label every record as synthetic. A customer cannot set, clear or forge the marker.
5. **Append-only evidence is retained and labelled.** Evidence and ledger rows created by synthetic
   tenants are never deleted. They carry the marker so queries, exports and reviews can exclude or isolate
   them. This is also the durable proof of what each run exercised (C-049: the label is the honest
   disclosure).
6. **Mutable data is cleaned through product paths.** After each run the harness uses the product's own
   revoke and cancel operations where they exist: revoke provider connections (which deletes the
   `customer-connection-` secret version), cancel test-mode subscriptions, and remove Keycloak users. It
   does not issue privileged deletes against product storage.
7. **Synthetic data only.** Names, emails, phone numbers and business details are generated and carry a
   reserved synthetic domain or sandbox number. No real person's data is used (C-063).
8. **Sandbox providers only.** Razorpay test mode, a Meta development-mode app with test users and a test
   Page, and the WhatsApp sandbox number. The harness verifies provider mode before acting (test key
   prefix, sandbox identifiers) and stops with a configuration finding if a live credential is detected.
9. **Environments.** Permitted in Demo and UAT where the acceptance profile exists. Production is
   prohibited until a later ADR amendment is accepted by the Founder.
10. **Volume and retention bounds.** One run per environment at a time (workflow concurrency). Synthetic
   tenant count and evidence volume per environment are reported each run; a configured ceiling stops
   further runs with a clear result. Retention of synthetic evidence follows the environment's
   constitutional evidence policy; no deletion path is introduced.
11. **Isolation probe.** Customer B exists so the harness can prove customer A cannot read B's data and
    that A's session cannot be used to enumerate B's identifiers.

## Alternatives Considered

| Option | Why not chosen |
|---|---|
| Delete synthetic evidence after each run | Violates C-027 and AD-003; would require privileged delete paths that weaken the ledger. |
| One fixed test customer reused forever | Trial and first-payment paths run once; repeat runs would test different code than a new customer meets. |
| Separate acceptance database or tenant-less sandbox | Tests a different system from the one customers use. |
| Marker as a JWT claim the customer's session carries | A claim is not authority (ADR-003) and could be forged if the realm is misconfigured; trusted-path write is required. |
| Scripted Google or Facebook sign-up | Violates provider terms, brittle, not automatable at the email challenge. Local users exercise the real login form instead; brokered first login stays `NOT-COVERED`. |
| Keycloak fine-grained admin permissions v1 to limit the provisioner to a group | Preview feature in the deployed Keycloak 25 line; would add a feature flag to the identity edge for a test capability. Revisit when the deployed version supports the stable v2. |
| Provisioning client with `manage-users` and compensating controls | **Chosen** (item 2): reuses the accepted lifecycle-writer role pattern; risk bounded by secret scope, harness refusal, admin-event audit and Demo/UAT-only. |

## Consequences

- Fidelity: each run meets the product as a brand-new customer.
- Cost: synthetic evidence accumulates; volume is bounded and reported.
- Dependency: Business Platform gains the marker registry, the internal route and the exclusions in
  reporting, billing aggregation and messaging suppression (decided in items 4 to 6, built by WC-159).
- Residual risk: the provisioning client can act on any realm user at the Keycloak layer; the controls in
  item 2 reduce but do not remove that. Demo and UAT only.

## Security And Exit

The provisioning client holds `manage-users` and nothing else: no product, billing or deployment
authority. If the Founder withdraws the capability, disable the workflow and the provisioning
identity; existing labelled evidence stays inert and excluded.

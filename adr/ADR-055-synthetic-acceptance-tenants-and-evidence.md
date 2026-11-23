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
   actor; B, the isolation probe) in the target environment's real Keycloak realm, through a dedicated
   provisioning identity limited to creating and deleting users in a `synthetic` group. Credentials are
   generated per run and held only in memory and masked job output. Customers are removed from Keycloak
   when the run ends.
2. **Same code paths.** A synthetic tenant uses the same registration, entitlement, billing, evidence and
   authority code as any customer. The marker never skips a control, so the run proves real behaviour
   (C-023).
3. **The marker reduces side effects only.** A synthetic marker and run identifier are written to the
   tenant by a trusted provisioning path. They are never derived from customer-controlled input, never
   grant authority, and are honoured only to (a) exclude the tenant from business metrics, revenue and
   customer-facing aggregates, (b) suppress delivery to any recipient other than a registered sandbox
   recipient, and (c) label every record as synthetic. A customer cannot set, clear or forge the marker.
4. **Append-only evidence is retained and labelled.** Evidence and ledger rows created by synthetic
   tenants are never deleted. They carry the marker so queries, exports and reviews can exclude or isolate
   them. This is also the durable proof of what each run exercised (C-049: the label is the honest
   disclosure).
5. **Mutable data is cleaned through product paths.** After each run the harness uses the product's own
   revoke and cancel operations where they exist: revoke provider connections (which deletes the
   `customer-connection-` secret version), cancel test-mode subscriptions, and remove Keycloak users. It
   does not issue privileged deletes against product storage.
6. **Synthetic data only.** Names, emails, phone numbers and business details are generated and carry a
   reserved synthetic domain or sandbox number. No real person's data is used (C-063).
7. **Sandbox providers only.** Razorpay test mode, a Meta development-mode app with test users and a test
   Page, and the WhatsApp sandbox number. The harness verifies provider mode before acting (test key
   prefix, sandbox identifiers) and stops with a configuration finding if a live credential is detected.
8. **Environments.** Permitted in Demo and UAT where the acceptance profile exists. Production is
   prohibited until a later ADR amendment is accepted by the Founder.
9. **Volume and retention bounds.** One run per environment at a time (workflow concurrency). Synthetic
   tenant count and evidence volume per environment are reported each run; a configured ceiling stops
   further runs with a clear result. Retention of synthetic evidence follows the environment's
   constitutional evidence policy; no deletion path is introduced.
10. **Isolation probe.** Customer B exists so the harness can prove customer A cannot read B's data and
    that A's session cannot be used to enumerate B's identifiers.

## Alternatives Considered

| Option | Why not chosen |
|---|---|
| Delete synthetic evidence after each run | Violates C-027 and AD-003; would require privileged delete paths that weaken the ledger. |
| One fixed test customer reused forever | Trial and first-payment paths run once; repeat runs would test different code than a new customer meets. |
| Separate acceptance database or tenant-less sandbox | Tests a different system from the one customers use. |
| Marker as a JWT claim the customer's session carries | A claim is not authority (ADR-003) and could be forged if the realm is misconfigured; trusted-path write is required. |
| Scripted Google or Facebook sign-up | Violates provider terms, brittle, not automatable at the email challenge. |
| Direct Keycloak admin with broad rights | Excess privilege; group-limited provisioning keeps blast radius small. |

## Consequences

- Fidelity: each run meets the product as a brand-new customer.
- Cost: synthetic evidence accumulates; volume is bounded and reported.
- Dependency: the platform needs a trusted way to mark tenants and honour the marker in reporting, billing
  aggregation and messaging suppression. Where Keycloak cannot restrict provisioning to a group in the
  deployed version, implementation stops and returns to this ADR (stop condition in WC-157).

## Security And Exit

The provisioning identity can only create and delete `synthetic` users; it holds no product, billing or
deployment authority. If the Founder withdraws the capability, disable the workflow and the provisioning
identity; existing labelled evidence stays inert and excluded.

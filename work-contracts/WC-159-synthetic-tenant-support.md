# WC-159 - Synthetic Acceptance Tenant Support

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-159 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-158 |
| Founder assignment | Current conversation, 2026-11-23: "Synthetic customer for testing"; ADR-055 accepted including the provisioning-client residual risk for Demo and UAT; implementation code authorized for this session |
| Status | IMPLEMENTATION_AUTHORIZED. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` at `018d196e184e6a29f5ec4264bfe80d9134ea0cd4` |
| Branch | `ib/158/synthetic-acceptance-customers` |
| Decisions | ADR-055 (accepted); ADR-003, ADR-009, ADR-044, ADR-046, ADR-053 preserved |
| Controlling specification | `architecture/reference/acceptance/customer-journey-acceptance-architecture.md` sections 5, 13 (T1, T2, T3, T10, T11); ADR-055 |
| Requirement ledger | [WC-159-requirements.yaml](./WC-159-requirements.yaml) |
| Constitutional basis | C-023, C-027, C-049, C-063, C-065, C-066 |

## Authority And Scope

### In scope

1. **Marker registry (Business Platform).** A server-side registry of synthetic subjects (Keycloak `sub` plus run
   identifier), default-off through a feature setting that exists only in Demo and UAT, written only through an
   internal route that accepts a Keycloak token carrying the realm role `acceptance-provisioner`.
2. **Marker effects.** A tenant created at first login by a registered subject inherits the marker. The marker only
   (a) excludes the tenant from business metrics, revenue and customer-facing aggregates, (b) suppresses delivery to
   any recipient other than a registered sandbox recipient and (c) labels records as synthetic. It never grants
   authority and never skips a control.
3. **Identity provisioner (harness module).** Creates and removes the run's two synthetic Keycloak users with the
   reserved username prefix, the `synthetic` group, a verified synthetic email, a generated password and OTP
   credential, through the `waooaw-acceptance-provisioner` client; refuses any other user; checks Keycloak admin
   events after the run; cleans up.
4. **Authored infrastructure and configuration** (files only): the acceptance OIDC identity with Key Vault, Reader and
   Monitoring Reader scope; the Keycloak client and realm role; the secret-catalog entries; rotation class.

### Out of scope and prohibited

- Applying Terraform, creating the Keycloak client or role, or creating or reading any secret in any environment.
- Any marker behavior that grants authority, skips a control or is derived from customer-controlled input.
- Enabling the registry in Production, or any customer-visible change when the setting is off.
- The harness core (WC-158) and journey content (WC-160).

## Inputs

| Input | Status |
|---|---|
| ADR-055 | ACCEPTED by the Founder, 2026-11-23 |
| `standards/PLATFORM-SETTINGS-AND-ACCESS-POLICY.md` S1-S7 | Present on `main` |
| Existing `pricing_admin` role route pattern and `keycloak-lifecycle-writer-client` pattern (WC-123) | Present on `main` |
| Founder authorization of implementation code in this session | Present (current conversation) |

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC159-R001 | The marker registry route and effects are off when the feature setting is off, the setting exists only for Demo and UAT, and Production rejects enabling it |
| WC159-R002 | The registry route accepts only a verified Keycloak token with realm role `acceptance-provisioner`; every other caller, including a customer, is refused and cannot set, clear or forge the marker |
| WC159-R003 | A tenant created at first login by a registered `(iss, sub)` inherits the marker; membership still comes only from the verified `(iss, sub)` and the marker is never read from a token claim or request body |
| WC159-R004 | Synthetic tenants are excluded from business metrics, revenue and customer-facing aggregates, and every record they create is labelled synthetic; append-only evidence is retained, never deleted |
| WC159-R005 | Delivery from a synthetic tenant to any recipient other than a registered sandbox recipient is suppressed and counted |
| WC159-R006 | The marker never skips authentication, authorization, entitlement, billing or evidence: a synthetic tenant is refused exactly as any customer would be |
| WC159-R007 | The provisioner creates only users with the reserved prefix in the `synthetic` group, with a verified synthetic-domain email, a generated password and an OTP credential, and removes them at the end of the run |
| WC159-R008 | The provisioner refuses to read, change or delete any user outside the reserved prefix (guarded by a test), and a post-run admin-event check fails the run on any other touched user (F18) |
| WC159-R009 | Credentials are generated per run, held in memory and never printed; the provisioner output passes the artifact secret scan |
| WC159-R010 | Cleanup leaves zero `synthetic` Keycloak users older than 24 hours and reports synthetic subscriptions or relationships that no customer path can end (F13) |
| WC159-R011 | The acceptance identity authored in the foundation Terraform module is off by default, Demo and UAT only, federated to the acceptance workflow on `main`, read-only on exactly the listed `acceptance-` and Razorpay test secrets, Reader on the resource group, Monitoring Reader on the workspace, with no Contributor and no role-assignment rights (F16) |
| WC159-R012 | The provisioning client fragment exists only for Demo and UAT, carries realm-management `manage-users` (ADR-055 decision 2), the read-only `view-events` role needed for the post-run admin-event audit, the `acceptance-provisioner` realm role and the `waooaw-platform` audience, is not in the production realm, and follows the 90-day versioned-overlap rotation class |

## Definition Of Done

1. Every requirement above has direct executable evidence run in Docker at the exact head: .NET tests in the
   Business Platform runner, harness tests in the TypeScript runner, Terraform and Keycloak configuration checks in the
   repository's Docker validators.
2. Keycloak real-form login and OTP step-up of a provisioned local user (proof of concept POC-1) needs the local auth
   preview stack or a deployed environment. It was not run in this contract's session; the harness creates the user
   with the documented credential representation and the claim stays unproven until the first run, which reports it.
3. Platform state refreshed in Docker; PR body prepared with `scripts/prepare_pr_body.sh`; author review recorded for
   the exact head; Founder reviews and merges.
4. No Terraform apply, secret entry or Demo execution is claimed.

## Stop Conditions

- Any marker behavior that grants authority or bypasses a control (ADR-003, C-023).
- Any need for a service token, direct database access or an ADR-046 route grant by the harness.
- A change that alters behavior for real customers when the setting is off.
- A cited identifier that does not exist.

## Implementation Record

Evidence at the exact head is in the PR body.

- **Setting and routes.** `feature_settings.acceptance_synthetic_tenants_enabled` (runtime `AcceptanceSyntheticTenants__Enabled`), default off, refused for production in the deployment-inputs script, in Terraform and at Business Platform start-up. Routes: `POST|PUT|DELETE internal/v1/acceptance/runs/{runId}/...` guarded by realm role `acceptance-provisioner` and `azp = waooaw-acceptance-provisioner`; the issuer is the verified token's, never the body.
- **Persistence.** Four append-only tables in `business` (`synthetic_subjects`, `synthetic_sandbox_recipients`, `synthetic_tenants`, `synthetic_delivery_suppressions`) in `99zzzzzzzz-wc159-01-synthetic-acceptance-registry.sql`; registrations expire after 24 hours; recipients are stored as a digest only.
- **Effects.** Tenant inheritance at cohort creation, delivery suppression in the WhatsApp adapter after every authority check, and span tagging. Business Platform has no cross-tenant revenue or business aggregate today; Billing Engine exclusion can read `business.synthetic_tenants` and is not granted here. Evidence rows are labelled through the tenant join, not stamped.
- **Provisioning client scope.** `view-events` (read-only) is added to `manage-users` because the post-run admin-event audit (ADR-055 decision 2c) cannot read events without it. The Keycloak client is authored as a realm fragment and is not applied; the Terraform identity is authored in the foundation module and is off by default.
- **Known pre-existing failure.** `tests/pipeline/test_wc124_init_chain_lint.py::test_repository_init_chain_meets_the_idempotent_authoring_standard` reports findings in wc134, wc136 and wc148 init files that this contract did not touch; the new file has none.
- **Not run:** `wc124_init_chain_local.sh`, Keycloak real-form and OTP login (POC-1), Terraform plan against Azure, any apply.

# ADR-054 - Customer Journey Acceptance

**Status:** PROPOSED - awaiting Founder acceptance
**Date:** 2026-11-23
**Decision owner:** Enterprise Architecture (INST-004)
**Authorization:** Founder assignment in the current conversation, 2026-11-23 (architecture package only; no implementation)
**Work Contract:** WC-157
**Constitutional basis:** C-023, C-027, C-042, C-049, C-059, C-063, C-065, C-071, C-080, C-086
**Capabilities:** 6.3 Record Constitutional Evidence; 6.4 Observe Platform Health and Constitutional Compliance; 6.7 Implement Governed Cloud Delivery
**Drivers:** AD-002, AD-004, AD-006, AD-008, AD-009, AD-010
**Preserved decisions:** ADR-003, ADR-014, ADR-046, ADR-050, ADR-053; `standards/PLATFORM-SETTINGS-AND-ACCESS-POLICY.md` S1-S5
**Companion:** ADR-055 (synthetic acceptance tenants and evidence)
**Controlling architecture:** `architecture/reference/acceptance/customer-journey-acceptance-architecture.md`

## Context

WAOOAW has unit, integration and fixture-based browser tests, but no automated check that a deployed
environment lets a customer complete the journey the product promises. The existing
`E2E - Acceptance Scenarios - Accessibility` workflow is disabled, also triggers on push to `main`,
targets QA by default, and the Playwright specs run against fixture sessions and canned content, not
against real services end to end. Delivery
contracts (WC-134, WC-136, WC-148, WC-149) each record behaviour that "only a Demo deployment can
prove". Several screens report success from emulators (for example the Facebook service reports
`PUBLISHED` without calling Meta), so a UI-only assertion cannot be trusted.

The Founder requires a manually triggered, fully automated post-deployment check that behaves like a
customer, states its coverage and depth, runs against Demo first and any other environment by a
parameter, and reports without blocking promotion.

## Decision

1. **One manual workflow.** `customer-journey-acceptance.yaml` is `workflow_dispatch` only. It has no
   push, pull-request or schedule trigger. Inputs: `environment` (choice; `demo` default) and `journey`
   (choice of versioned journey definitions; slice 1 first). GitHub requires choice options to be static
   text, so adding an environment is one profile file plus one option line; a static test fails if the
   option list and the profile files differ, and an environment without a profile cannot run.
2. **Journey as data.** A journey is a versioned YAML document validated against a schema. Each step
   names the customer stimulus, the claims the product makes after it, the witnesses that must agree,
   and the requirement and story identifiers it proves. The runner contains no journey logic.
3. **Customer stimulus through the real UI.** Playwright drives the deployed web application, signing
   in through the real Keycloak with a run-scoped synthetic customer (ADR-055). No fixture, route
   mock, service token or direct database access is used.
4. **Three-witness oracle.** Every claim ("Paid", "Active", "Connected", "Published") must be agreed by
   (W1) what the screen shows, (W2) the platform record read through customer-facing APIs under the
   synthetic customer's own session, and (W3) the provider sandbox read through the provider's API.
   Disagreement fails the claim. Absence of a witness is reported as `NOT-WITNESSED`, never as pass.
5. **Closed verdict vocabulary** per step and per stage: `PASS`, `FAIL`, `BLOCKED-BY-FLAG`,
   `NOT-COVERED`, `NOT-WITNESSED`, `ENV-UNAVAILABLE`, `FLAKY`. The run reads the environment's effective
   settings first so a feature turned off is reported as `BLOCKED-BY-FLAG`, not as pass or failure.
6. **Coverage is measured against requirements, not lines.** A step cites `WCNNN-RNNN` requirement IDs
   and `AE-nn-Snn`/`PG-nn` identifiers. The report states, per identifier, the deepest level reached:
   L1 rendered, L2 acted on, L3 state changed, L4 evidence recorded, L5 failure path handled. Depth of
   system reach is reported as the services and endpoints the customer traffic touched against the
   component registry.
7. **Always-on guards** evaluate every page and response in every journey: secret or token patterns,
   foreign-tenant identifiers, personal-data leakage, WCAG 2.1 AA violations, Emergency Stop reachability
   and Evidence-First ordering where observable.
8. **Report-only verdict.** Nothing consumes the verdict to block promotion. The workflow conclusion
   mirrors the verdict: red when any step is `FAIL` or the environment is `ENV-UNAVAILABLE` (nothing was
   verified); green otherwise. `NOT-WITNESSED`, `FLAKY`, `BLOCKED-BY-FLAG` and `NOT-COVERED` appear as
   warnings at the top of the summary and never as passes. No required check, deployment gate or branch
   rule may depend on the workflow until a later ADR amendment is accepted by the Founder.
9. **Secrets live only in Azure.** The workflow authenticates with an acceptance-only Azure OIDC
   federated identity, distinct from the deployment identities (C-065), with read-only access to Key
   Vault secrets prefixed `acceptance-` and to the environment's existing Razorpay test secrets by exact
   name (`razorpay-test-key-id`, `razorpay-test-key-secret`, `razorpay-test-webhook-secret`, already
   consumed by the Billing Engine). No GitHub environment secret or variable carries a credential.
   Environment addresses are non-secret data in git (settings policy S1, S3).
10. **Docker-only execution** (C-080, ADR-050): the harness runs in a digest-pinned, attested runner image
    through the validation-gate action.
11. **Binding to the candidate.** The report records the deployed image digests, the repository commit,
    the environment profile digest and the journey definition digest, so a verdict applies to an exact
    deployed candidate.
12. **Environment availability is a result.** The run begins with a health and readiness probe. A stopped
    or unreachable environment yields `ENV-UNAVAILABLE`; the workflow never starts or stops an
    environment.
13. **Cost bound.** One slice-1 run must fit the AD-006 non-production budget: no paid provider traffic
    except sandbox-mode providers, and bounded AI generation through the existing governed path.

## Alternatives Considered

| Option | Why not chosen |
|---|---|
| Revive the disabled E2E workflow | Push-triggered, QA-targeted, fixture-based; conflicts with manual-only and real-stack requirements. Its Docker gate pattern is reused instead. |
| Fixture-based Playwright against Demo | Proves screens, not product behaviour; cannot detect emulated success. |
| Single-witness UI assertions | An emulator or stale cache passes. Rejected by the Founder's depth requirement. |
| Direct database assertions | Bypasses ADR-003 tenant authority, couples tests to schema, needs privileged credentials. |
| Adopt a commercial synthetic-monitoring or test-orchestration product | Needs access to Demo, Keycloak and provider sandboxes from a third-party boundary, adds data egress (C-063) and cost (AD-006). Playwright is already in the repository and is open source. |
| AI-persona exploratory testing as the verdict | Non-deterministic; allowed only as a later non-deciding companion under AI Resource Governance. |
| Run on every push or schedule | Founder asked for a manual trigger after deployment completes. |

## Lifecycle Maturity

Playwright and Keycloak OIDC are established and already in use here. Razorpay test mode and Meta
development-mode apps are provider-supported features. WhatsApp sandbox numbers only message verified
recipients, so inbound behaviour is exercised through signed webhook delivery to the environment's own
endpoint (ADR-053 signature rules apply), not through a real handset.

## Consequences

- WAOOAW gains a requirement-traced, evidence-backed statement of what works live and what was not tested.
- Emulator-backed success is detected by the second and third witnesses.
- Each run creates synthetic tenants whose append-only evidence persists (ADR-055).
- Provider sandboxes become environment dependencies with Key Vault entries to maintain.
- A red verdict does not stop a release; the Founder reads it.

## Security, Operability And Cost

- Least privilege: read-only `acceptance-` secrets; no deployment authority; no service tokens; customer
  session only for platform reads.
- Output hygiene: artifacts are scanned for secret patterns before upload; traces and videos mask password
  and token inputs; a leak finding fails the run and withholds the artifact.
- Operability: one workflow, one journey schema, one report schema; flaky steps are recorded, never
  silently retried.
- Cost: GitHub-hosted minutes plus Azure reads and sandbox-mode provider calls only.

## Exit And Reversibility

Disabling the workflow removes the capability with no effect on product behaviour. The journey and report
schemas are product-neutral YAML and JSON. Playwright may be replaced without changing journey definitions.
Synthetic tenants follow the retention rule in ADR-055.

## Fitness Obligations

The measurable checks are in section 9 of the controlling architecture and become requirements of the
implementing Work Contracts.

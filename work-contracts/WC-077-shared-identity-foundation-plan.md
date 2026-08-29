# Work Contract 077 - Shared Identity Foundation Implementation Plan

**Office:** Chief Solution Architect (INST-005)
**Future executor:** Platform IT Expert (INST-010)
**Assigned by:** Founder instruction, 2026-08-29
**Status:** IMPLEMENTATION AUTHORIZED FOR CURRENT SESSION 2026-08-29; CLOUD EXECUTION NOT AUTHORIZED
**Delivery unit:** Component 2 - Shared Identity Foundation implementation plan
**Constitutional basis:** C-023, C-032, C-059, C-063, C-065, C-071, C-076, C-080, C-100

## Objective

Produce a detailed, self-sufficient implementation plan for a shared authentication and authorization
foundation that reuses Keycloak, the Business Platform Identity Boundary, and the Phone Identity
Service. The implementation must support web and mobile clients through Keycloak-issued tokens and
WhatsApp through ADR-023 phone proof and an internal Business Platform adapter, without duplicating
provider integration or allowing a WhatsApp proof to become a web or mobile session directly.

The plan is recorded in
`architecture/foundation-consolidated-assessment-2026-08-29.md`, Work Component 2. It must define
the exact boundaries, contracts, tasks, tests, review gates, external prerequisites, Docker-only
validation, cloud alignment, and immutable Demo-to-UAT-to-Production promotion rules needed by
INST-010 so that implementation does not require an architectural or security decision.

## Authority And Scope

The Founder accepted ADR-048 and the remediated identity package and authorized INST-010 to implement
this plan in the current session on 2026-08-29. This permits the repository source, test, workflow,
image, and infrastructure changes required for ID-00 through ID-07. Provider activation and cloud,
DNS, deployment, customer-traffic, UAT, and Production changes retain their independent gates.

The future implementation scope described by the plan is:

1. Keycloak-brokered Google, Meta/Facebook, Apple, and approved email-fallback authentication.
2. Business Platform identity and authorization APIs consumed through generated clients by web and
   future mobile applications.
3. Internal WhatsApp phone-proof continuation and proof-gated account linking under ADR-023.
4. Environment-specific identity configuration for Demo, UAT, and Production.
5. Docker-only unit, contract, integration, security, CCT, and environment acceptance evidence.
6. Build-once immutable image promotion from Demo to UAT and later Production.

Out of scope are direct application-to-provider OAuth, a new authentication microservice, direct
WhatsApp-to-Keycloak token exchange, frontend visual implementation, provider account creation,
unapproved provider activation, UAT or Production mutation, and Production traffic activation.

## Required Inputs

| Input | Required state | Purpose |
|---|---|---|
| `architecture/reference/components/identity-boundary.md` | Canonical, but its gate table must be rechecked before implementation | Component ownership, assurance, state, API, error, privacy, and gate contract |
| `architecture/reference/api-specs/business-platform.openapi.yaml` | Canonical OpenAPI 3.1 | Public identity API and generated-client source |
| `architecture/reference/components/identity-edge.md` | Proposed; applies only after ADR-048 acceptance | Exact public OIDC routes, controls, privacy, failure, and evidence contract |
| `architecture/reference/pipeline/identity-dependency-manifest.md` | Founder-review candidate | Signed dependency/configuration binding, promotion, compatibility, and rollback contract |
| `adr/ADR-008-keycloak-identity-broker.md` | Accepted v3 | Provider federation and token authority |
| `adr/ADR-023-whatsapp-phone-identity-c042-agents.md` | Accepted | WhatsApp proof, replay, and internal-token boundary |
| `architecture/reference/pipeline/azure-deployment-topology.md` | Canonical | Environment isolation, exact-six release, promotion, and cloud gates |
| `adr/ADR-047-private-ephemeral-deployment-runners.md` | Accepted | Private runner and cloud execution path |
| `architecture/reference/engineering-standards.md` | Active | Docker-only testing and service quality floor |
| `constitution/PROJECT_STATE.md` | Re-read at execution start | Current environment and cloud authority |

Before implementation, INST-010 must confirm that the identity contract's independent re-review
gate is closed and obtain explicit Founder authorization for the current implementation session.
Meta and Apple activation remain independently blocked until their named external prerequisites are
present and approved; blocked activation must not block provider-neutral implementation.

## Authorized Outputs

1. The expanded Work Component 2 implementation plan in the consolidated assessment.
2. This Work Contract as the authority, scope, input, completion, and stop record for plan authoring.
3. Founder-authorized focused Enterprise Architecture decisions for the unresolved identity ownership,
  role, identity-edge, release-dependency, and mobile-scope boundaries identified by INST-010.
4. Founder-authorized Solution Architecture remediation of the canonical identity component and
  OpenAPI contracts after the Enterprise Architecture decisions are recorded.
5. A final INST-010 implementation-readiness assessment against the remediated contracts.
6. Repository implementation and validation artifacts for ID-00 through ID-07 under the current
  Founder-authorized session; no environment deployment without separate authority.

## Focused Remediation Sequence

Founder authorization recorded on 2026-08-29 requires this bounded sequence:

1. INST-004 Enterprise Architect resolves only the architecture boundaries identified in the
  implementation-readiness review. It does not read or normalize source implementation.
2. INST-005 Solution Architect converts those decisions into complete component, API, data, error,
  configuration, compatibility, and test contracts. It does not produce runnable code.
3. INST-010 Platform IT Expert checks whether the resulting package can be implemented without
  architecture invention. Any remaining architecture gap stops implementation.

This sequence does not authorize an independent approval verdict, provider activation, source/test
changes, image build, cloud query or mutation, deployment, PR approval, or merge.

## Definition Of Done

- The plan separates architecture, engineering, external-provider, and environment authorization gates.
- It gives INST-010 ordered tasks with inputs, outputs, tests, evidence, rollback, and stop conditions.
- It preserves Keycloak as credential authority and Business Platform as the public identity facade.
- It defines web, mobile, and WhatsApp reuse without token-authority shortcuts.
- It mandates Docker-only tests, at least 90% affected-service line coverage, security and contract
  testing, author review, and Founder review before merge.
- It aligns with the current Azure private-runner design and immutable Demo-to-UAT-to-Production
  image-promotion contract.
- The complete authored output passes author review with no unresolved in-scope finding.

## Stops

- Stop before implementation unless the Founder explicitly authorizes writing implementation code
  for that session.
- Stop if the canonical identity contract remains unapproved or conflicts with the OpenAPI.
- Stop rather than integrate directly with Google, Meta, or Apple from an application service.
- Stop rather than exchange WhatsApp phone proof directly for a Keycloak web/mobile session.
- Stop provider activation when Meta or Apple external prerequisites are absent.
- Stop all cloud mutation without exact environment authority; Demo precedes UAT and Production.
- Stop on a secret in source, image, state, plan, log, test artifact, URL, or analytics payload.
- Stop on test skips, coverage below 90%, mutable image tags, rebuilt promotion images, or an
  unreviewed schema/migration compatibility result.
- Never self-approve or self-merge the implementation PR.

## Author Review

**Result:** PASS - plan and focused remediation complete, not implementation approval.

INST-005 reviewed this Work Contract and the complete Work Component 2 plan against the Founder
request, canonical identity boundaries, provider prerequisites, channel reuse, Docker-only quality
gates, cloud alignment, immutable promotion, rollback, and authorization stops. Findings concerning
specification-before-code ordering, absent mobile technology authority, customer-versus-institutional
freeze scope, and executable Docker command forms were repaired in the owning assessment. No
unresolved finding remains within plan-authoring scope.

The focused EA/SA remediation was also checked against the real canonical OpenAPI and database
boundary. It closes the in-scope token, customer-role, provider/session projection, Phone Identity
adapter, Identity Edge, environment configuration, dependency promotion, and non-destructive rollback
decisions. OpenAPI validation passes with the pinned generator; its two recommendations concern
pre-existing unused non-identity models. Platform IT requires no new in-scope architecture choice,
but must remain stopped until ADR-048 and the remediated package receive required acceptance and the
Founder explicitly authorizes implementation for that session.
# WC-120 - One-Pass Specialist Review And Repair Requests

## Purpose And Status

This record accompanies WC-120 and requests a single write-access review/contribution pass
from the owner offices required by the merged PR #498 enterprise architecture, §23. The
requests are to be submitted with the WC-120 pull request. Until each office responds, its
status is **PENDING**; listing an office or prior review is not evidence of approval.

The review scope is the WC-120 contract, requirement ledger, candidate PR #499 solution/API
crosswalk, and the exact owner controls identified below. Reviewers may record findings and
authorized repairs on the PR branch within their office boundary. The Chief Solution
Architect integrates and traces repairs. Each office returns one explicit scoped disposition,
with finding IDs and locations or an explicit no-findings statement. The author repairs
accepted findings in the same pass; a second review round is not requested. A new material
owner-boundary decision, unresolved conflict, or change outside the reviewed scope stops for
Founder direction.

These requests do not authorize implementation, provider or cloud mutation, deployment,
activation, traffic, Production changes, PR approval, or merge. No office disposition is
pre-recorded here.

## Existing Review Evidence

| Record | Scope and original disposition | Use in WC-120 |
|---|---|---|
| [R-146 Security review](../reviews/R-146-conversation-engine-whatsapp-security-review.md) | One-pass review of the PR #498 enterprise architecture; original verdict `CHANGES REQUIRED`. | Input constraints. PR #498 §27 maps author repairs; it is not a post-repair Security approval or a review of WC-120. |
| [R-147 Data review](../reviews/R-147-conversation-engine-whatsapp-data-review.md) | One-pass review of the PR #498 enterprise architecture; original verdict `CHANGES REQUIRED`. | Input constraints. PR #498 §27 maps author repairs; it is not a post-repair Data approval or a review of WC-120. |

The downstream office contributions requested below remain necessary. The PR #498 reviews
do not substitute for them.

## Requests

| Office | Requested one-pass review/contribution | Required disposition evidence | Status |
|---|---|---|---|
| Data Architect | Validate reuse and ownership of canonical conversation/message state; transaction, sequence, inbox/outbox, idempotency, tenant/RLS, payload and transcript lineage, retention/erasure/legal hold, backup/restore, and migration/rollback controls against WC-115 and PR #498 §15. Identify unresolved Data/Legal owner decisions rather than assigning them to the implementer. | Scoped pass/changes-required/no-findings disposition; exact WC120-R IDs and contract locations; accepted data-profile references and any owner-bound decisions/stop conditions. | PENDING - request to be submitted with this PR |
| Security Architect | Validate signed raw-byte webhook handling and freshness/replay behavior; ADR-023 phone identity and WC-115 assurance mapping; workload identity, audience/environment binding, secret rotation/revocation, media safety, Stop precedence, privacy-safe telemetry, and denial/no-mutation tests. | Scoped pass/changes-required/no-findings disposition; exact WC120-R IDs and contract locations; assurance and security-profile references; any stop condition. | PENDING - request to be submitted with this PR |
| Platform Architect | Validate Demo/UAT/Production ingress and isolation, DNS/TLS and callback ownership, optional egress, protected configuration, observability/alerting, recovery/teardown, rollback, and measurable WhatsApp-specific SLO ownership. Keep provider, DNS, cloud, and activation decisions separately authorized. | Scoped pass/changes-required/no-findings disposition; exact WC120-R IDs and contract locations; source of each SLO/operational target or an explicit readiness stop. | PENDING - request to be submitted with this PR |
| AI Architect | Validate server-resolved context/policy handoff, source/version lineage, research-versus-inference separation, prompt-injection handling, minimum necessary content, provider neutrality, and explicit unavailable/unknown behavior against WC-115 AIR controls. | Scoped pass/changes-required/no-findings disposition; exact WC120-R IDs and contract locations; accepted AIR profile references and any blocked behavior. | PENDING - request to be submitted with this PR |
| Product Owner | Validate customer journeys, consent, service-window/template behavior, accessible and low-literacy states, voice/media correction, context transitions, explicit conclusions, and unsupported/degraded customer-visible outcomes. | Scoped pass/changes-required/no-findings disposition; exact WC120-R IDs and contract locations; customer acceptance conditions and any unresolved product decisions. | PENDING - request to be submitted with this PR |
| Test Champion | Validate bidirectional CE-FIT-01..16 traceability; direct positive, negative, concurrency, replay, recovery, privacy, environment, and rollback oracles; repository-native targeted test selection and exact evidence binding. | Scoped pass/changes-required/no-findings disposition; exact WC120-R IDs and contract locations; executable oracle/evidence gaps and exact-candidate qualification gate. | PENDING - request to be submitted with this PR |

## Repair And Closure Rule

The Chief Solution Architect records each accepted finding against a stable WC120-RNNN
requirement, repairs the contract or ledger, and records the exact resulting evidence in the
PR. A finding requiring a new accepted decision or owner boundary is not repaired by
assumption; WC-120 remains gated until the authorized owner supplies the decision. A clean
review disposition establishes only the office's stated contribution and does not accept
WC-120, authorize implementation, or approve deployment or activation.

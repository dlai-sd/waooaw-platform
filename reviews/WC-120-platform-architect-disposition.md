# WC-120 Platform Architect Disposition

## Review Control

| Field | Value |
|---|---|
| Work Contract | WC-120 |
| Reviewer | WAOOAW Platform Architect, INST-009 |
| Review mode | Founder-requested single-pass review and repair with write access |
| Date | 2026-10-13 |
| Scope | Environment topology; ingress; DNS/TLS/callback ownership; egress; protected configuration; telemetry/alerting; recovery, teardown, and rollback boundaries; WhatsApp service objectives |
| Authority exercised | Platform Architecture values, controls, oracles, alert thresholds, and ownership were selected and written into WC-120. No provider, cloud, DNS, deployment, traffic, activation, recovery, teardown, rollback, Production, or implementation action was performed. |

## Exact Source And Repair Pins

| Source | Exact target |
|---|---|
| Repaired WC-120 | `work-contracts/WC-120-conversation-engine-whatsapp-implementation.md`, SHA-256 `c27143f1e97ac6bb2d498a7c756fbf96cd5ca3fc69acfe6b7389deb80036c308`, especially §3.3, R016-R020/R023/R026/R041, and §§8-10 |
| Requirement ledger | `work-contracts/WC-120-requirements.yaml`, R016, R017, R023, and R041 |
| Fitness matrix | `work-contracts/WC-120-fitness-evidence-matrix.yaml`, `platform_slo_profile` and CE-FIT-07/09/12/13/14/16 |
| PR #498 enterprise package | `architecture/reference/components/conversation-engine-whatsapp-enterprise-architecture.md` at merged commit `4a4420af6ee132623d6b87eb3863d700e56c9b86`, §§13, 15.9-15.10, 17-18; ADR-053 at the same commit |
| PR #499 solution package | `architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md`, blob `224d8f43f2a46e810eb5b13aac35570b6f0ebcda`, §§11, 13-16, 19.2, and 20 |
| Existing owner contracts | Conversation Core blob `1004255bbd01e3d10dd53a64a2b115ac059ad631`; WC-114 blob `11ba639efa43d3288ba1eb39fd2e05308c42e6c0`; WC-115 blob `337fcef0a51a4c2ef2ff72423a7afc64969d8914` |

## 1. Repaired And Closed Platform-Owner Findings

| Finding | WC120-R / fitness mapping | Exact repair and closure |
|---|---|---|
| `PA-120-01` — Environment trust assets and anti-collision oracle were incomplete. | R018-R020, R041; CE-FIT-12 | **CLOSED.** Demo/UAT/Production have distinct phone/provider identity, app/WABA, hostname/certificate, secret/workload access, dedup/replay, data/media, telemetry/alerts, templates, and deployment authority. Cross-environment fallback or mutation target is `0`. |
| `PA-120-02` — Ingress and callback ownership needed exact boundaries. | R009, R018-R020, R041; CE-FIT-09/12 | **CLOSED.** Host patterns are `whatsapp-demo.<approved-domain>`, `whatsapp-uat.<approved-domain>`, and `whatsapp.<approved-domain>`. Demo ingress is stable for its authorized lifetime, UAT ingress is stable, and Production is stable/dark. Platform owns authorized Azure ingress/DNS/TLS routing; provider/configuration operations own app/WABA callback registration; runtime has read-only binding authority. |
| `PA-120-03` — Ingress stability could imply stable egress. | R012, R023, R041; CE-FIT-07/16 | **CLOSED.** No stable egress exists by default. An environment-specific address is permitted only after an authorized allow-list dependency is proved. Ingress and egress trust stay separate; isolated-restore provider egress target is `0`. |
| `PA-120-04` — Protected configuration and workload separation needed an enforceable oracle. | R008-R009, R018-R020, R028, R038, R041; CE-FIT-12 | **CLOSED.** Complete identities, provider IDs, hosts/certificates, and secrets remain environment-protected. Adapter, scanner, and configurator have separate identities/audiences. Catch-all credentials, cross-environment read, and rollback restoration of revoked authority are prohibited. |
| `PA-120-05` — Telemetry ownership, privacy, and routing were not measurable. | R017, R026, R041; CE-FIT-14 | **CLOSED.** Prohibited telemetry/dead-letter disclosure target is `0`. Any isolation/privacy/Production-dark/Stop-hard-ceiling event is detected within 1 minute, paged within 5, acknowledged within 10, and fenced within 30. Platform Operations owns routes/runbooks; emitters own signal correctness; Security/Data retain privacy/retention ownership. |
| `PA-120-06` — Recovery and rollback authority was ambiguous. | R023, R026, R041; CE-FIT-16 | **CLOSED for Platform.** Restore starts isolated/non-routable with separate temporary authority and zero provider egress. Platform executes infrastructure only under separate authority; application rollback preserves additive history/evidence and cannot reverse provider, DNS, or customer-visible effects. Numeric data recovery policy remains the named external dependency below. |
| `PA-120-07` — Demo teardown had no exact no-impact oracle. | R018, R026, R041; CE-FIT-16 | **CLOSED.** Callback acceptance is disabled first; unresolved work is reconciled or isolated through retry/dedup/hold/erasure horizons; temporary authority is revoked under owner policy; required tombstones/evidence remain; UAT/Production binding changes equal `0`. Execution remains separately authorized. |
| `PA-120-08` — Platform-owned WhatsApp service objectives and alerts were absent. | R016-R017, R041; CE-FIT-07/09/12/13/14 | **CLOSED.** §3.3, R041, and `platform_slo_profile` now contain exact targets, windows, low-volume behavior, alert triggers, response clocks, and evidence ownership. |
| `PA-120-09` — Production-dark readiness could be mistaken for activation authority. | R020, R027, R041; CE-FIT-12 | **CLOSED.** Production-dark checks are synthetic and non-routing. Purchase, provider/app creation, DNS/provider mutation, deployment, traffic, activation, recovery, rollback, and cancellation each require separate authority. |

## Closed Platform Service Targets

| Objective | Exact accepted Platform target |
|---|---|
| Callback ingress availability | Demo `>=99.0%` per rolling 24 eligible hours; UAT `>=99.9%` per rolling 30 eligible days; Production `>=99.95%` per calendar month only after separate activation |
| Durable signed-event acceptance | Trusted receipt through atomic durable outcome: `p95 <=1 s`, `p99 <=2 s`, every eligible request `<=5 s`, rolling 15 minutes; below 100 events, apply the per-event ceiling plus synthetic probe |
| Outbound queue/reconciliation | First attempt `p95 <=30 s`, `p99 <=60 s`; oldest eligible queue item `<=120 s`; unknown outcome durably terminal or explicitly `UNRESOLVED` within `15 min` |
| Emergency Stop | Durable verified receipt to BP/PR latch: `p95 <=1 s`, `p99 <=2 s`, hard ceiling `5 s`, rolling 15 minutes |
| Availability alert | Page on `>=14.4x` 1-hour or `>=6x` 6-hour error-budget burn; delivery `<=5 min`, acknowledgement `<=15 min`, mitigation start `<=30 min` |
| Latency/queue alert | Page when acceptance `p99 >2 s` for 5 minutes, any request `>5 s`, queue age `>120 s` for 5 minutes, or unknown outcome `>15 min` |
| Zero-tolerance controls | Cross-environment mutation, isolated-restore provider egress, prohibited telemetry disclosure, and Demo-teardown UAT/Production changes each equal `0` |

## 2. Exact External Dependencies And Named Owners

These items do not reopen a Platform finding. They stop only the affected stage or action.

| Dependency | Named owner | Exact stop |
|---|---|---|
| Per-environment recovery profile | Data Architect, INST-006; Founder accepts material cost/risk | Data has fixed Demo RPO/data loss `24h`, RTO `8h`; UAT RPO/data loss `4h`, RTO `4h`; Production RPO/data loss `15m`, RTO `2h`. WC120-R023 recovery/promotion qualification remains **BLOCKED** until Founder accepts those material limits and candidate-bound recovery evidence passes. |
| WhatsApp lifecycle-to-retention mapping, legal hold, and rights consequences | Data Architect, INST-006; Legal/Founder for protected policy | Affected persistence, erasure, and teardown steps remain **BLOCKED**; Platform teardown cannot delete or shorten an unaccepted class. |
| Approved domain, certificate/resource references, complete provider identifiers, callback registrations, credentials, and Production number | Authorized Platform/provider configuration operator; Founder for purchase/material action | Protected values remain outside repository artifacts. Their absence does not block specification closure but blocks the corresponding environment apply or activation. |
| Cloud/DNS/TLS/provider mutation, deployment, traffic, Demo/UAT activation, Production action, recovery, teardown, and rollback execution | Founder-authorized environment operator for the exact action | No action is authorized by this disposition; evidence planning and configuration contracts only. |
| Executable selectors and candidate-bound results for CE-FIT-07/09/12/13/14/16 | Implementation owners and Test Champion after implementation authorization | Expected-fail absent nodes are valid pre-implementation status. A PASS cannot be claimed until Docker-runner execution produces exact-candidate evidence. |

## 3. Final Disposition

**PASS**

All Platform Architect-owned findings are repaired and closed in the controlling WC-120 contract,
requirements ledger, and fitness matrix. WC120-R041 now has exact measurable values and is no longer
blocked by missing Platform targets. The named Data/Legal/Founder/provider/implementation
dependencies remain scoped stops for their affected stages; they are not unresolved Platform
Architecture decisions and do not authorize any external action.

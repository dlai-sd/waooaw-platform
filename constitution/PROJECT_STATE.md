# PROJECT_STATE.md

**State Schema:** 2.0.0
**State Revision:** 179
**Last Updated:** 2026-09-19 (WC-099 ITERATION 3 QUALIFICATION SAFEGUARDS CHECKPOINT)
**Purpose:** Current operational state for bootstrap, recovery, and automated sprint controls.

This file is a snapshot, not a session ledger. Keep it below 200 lines. Update the active
checkpoint in place; record durable detail in the owning Work Contract, Goal record, review,
or evidence artifact. Completed history remains in git and the archive index below.

---

## Institutional Snapshot

| Field | Current Value |
|---|---|
| Epoch | Epoch 1 — Foundation |
| Gate | G5 CLEAR — prerequisites met; not session implementation authority |
| Engineering status | IMPLEMENTATION |
| Platform version | 1.45.0 |
| Latest completed Work Contract | WC-080 - Agent Runtime Adapter Contract v1 |
| Latest merge | PR #442 merged to `main` as `b7472535` |
| Active delivery | WC-099 post-Demo correction, WC-100 Engineering Validation Efficiency, WC-098 Customer Registration Readiness, WC-097 Marketplace Acquisition Experience, WC-089 DMA Release 1, WC-093 public/auth experience finalization, WC-085 brokered authentication follow-up and WC-088 Customer Multi-Agent And Skill Journey; P3-EX11 remains plan-only |

## Active Checkpoint - GOAL-006 Phase 3 Live Execution

| Milestone | Status |
|---|---|
| WC-076 P3-EX01 through P3-EX07 | DONE - protected environments, OIDC, signed exact-six release, private runners, configuration and deployment controls merged |
| Canonical deployment entry | DONE - PR #371 retains only `.github/workflows/deploy.yaml` as the manual application entry and delegates deployment and independent verification |
| Demo deploy / verify | PASS - corrective run `33147562517`; exact-six inventory, healthy revisions, internal probes, Founder browser CIDR and cleanup passed |
| Founder Demo acceptance | ACCEPTED - Founder approved the corrected Demo application on 2026-08-28 |
| UAT runner delivery | PASS - preview `33149859100` and apply `33150103583`; private runner stack ACTIVE with zero residual executions |
| UAT deploy / verify | PASS - final run `33177257822`; exact-six, latest-ready revisions, functional checks, Web and OIDC endpoints passed |
| Cloud delivery consolidation | MERGED - PR #371 as `7211eb8`; temporary wrappers and deny-only promotion workflow removed |
| Lightweight workflow consolidation | MERGED - PR #388 as `72123e5`; release qualification moved into CI, runner operations consolidated, and durable workflows renamed by purpose |
| Current application foundation | DONE - PRs #373, #376, #381 and #386 added identity, public acquisition, admission and runtime adapter foundations after cloud qualification |
| Demo/runtime readiness repairs | MERGED - PRs #389 through #398 repaired cleanup provenance, cloud authority, dependency recovery, service startup, Temporal readiness and deployment verification |
| WC-078 public visual experience | ENGINEERING QUALIFIED - WC-01 through WC-08 complete; WC-09 Docker build/tests/browser matrix/54 captures/scanners and author review PASS; Founder visual acceptance, PR approval and merge pending |
| WC-084 Customer Portal | ENGINEERING QUALIFIED - generated-client-backed My Agents, Marketplace, Alerts, Profile, Settings, account drawer, Onboard/Induct and lifecycle views complete; Docker build/typecheck, 209 Jest tests, 96.33% changed-interaction line coverage, 40 focused BP tests and 238 Playwright tests pass; Founder visual acceptance, PR approval and merge remain |
| WC-085 remediation | PARTIAL / D-GOAL LOCAL PASS - Draft PR #409 on `ib/085/remediation`. Founder-accepted D-GOAL is implemented through the existing relationship command: append-only RLS decisions, exact versions, fresh assurance, idempotency, generated client and Operations relock. Full BP Docker suite passes 641/641 at 91.59% line / 80.17% branch; exact candidate image and scans are recorded in WC-085 evidence. The PR's original 19-alert CodeQL set is repaired; the first pushed scan closed 18 and its sole remaining StorageEvent warning has a constructor-free follow-up awaiting pushed-head closure. D-BILLING, D-IDENTITY, real Google, deployment and full story acceptance remain open. |
| WC-085 brokered authentication remediation | IN-PROGRESS CHECKPOINT - shared Google/Facebook broker handling, email-assurance separation, bounded identity-edge headers, minimal login/register UI, exact-origin Demo public-PKCE preview client and immutable-image Codespaces launcher are locally qualified. Demo deployment run `34760952302` reached Business Platform `ActivationFailed`: ASP.NET indexed binding appended the configured authorized parties to the non-empty options default, and strict distinct-party validation stopped the process. The fail-closed empty default, exact indexed-binding regression proof and deployment-shaped production-image startup gate now pass locally, including readiness and zero restarts under Azure CPU/memory limits. Preventive lifecycle simulation also found that the NextAuth session could outlive Keycloak's bearer: browser authentication, Founder authority and server bearer forwarding now fail closed when token expiry is missing or elapsed. Independent Google and Facebook redirect verification checks exact callbacks, provider client, scopes, state and trusted external hosts; the Facebook verifier restarts from Keycloak on bounded transient transport failures and fails closed after exhaustion. Release qualification runs `34771343987` and `34772119018` exposed that the local Azure emulator asserted a Google callback before reading the provider hint, so Facebook initiation closed the socket. The emulator now models both providers, both evidence files are required and retained through failure cleanup, and sanitized reason codes replace opaque verifier exceptions; the exact Docker Azure CLI rehearsal passes. Open-PR updates also support explicit pre-push binding of complete C-065 evidence followed by authoritative post-push verification. Hostile redirect cases, web tests and Chromium/Firefox/WebKit journeys pass locally. Trusted image publication, PR approval/merge, successful Demo redeploy, authorization-code exchange and real Google/Facebook account journeys remain. |
| WC-087 agent-instance foundation | MERGED - PR #411 as `28f3e5e4`; immutable per-relationship agent identity, exact admission/version binding, same-type multi-instance proof and PR trial binding are on `main`. |
| WC-088 customer multi-agent/skill journey | ENGINEERING QUALIFIED - canonical My Experts, relationship switching, four governed skill decisions, append-only/RLS persistence, generated OpenAPI client and two-agent isolation proof pass local Docker and web qualification; PR submission and Founder review/merge remain. |
| WC-089 DMA Release 1 | EXACT-SEVEN CODE QUALIFIED - DMA Release 1 remains independently admitted at `1.0.0` / specification `3.1` and is now the permanent seventh first-party release workload by Founder direction. CI build/scan/attestation, signed registry tuple, Compose, Terraform, private `ca-<environment>-dma` deployment, admission/image digest binding, PR credential enforcement, Log Analytics-bound structured logs, live inventory, independent probe, recovery and local Azure emulation are implemented. Docker qualification passes 209 release tests, 2 PostgreSQL checks, WC-091 data verification, release simulation, exact-seven inventory and the local Azure CLI end-to-end deployment rehearsal; the image also returns liveness `200`, authorized descriptor `200`, invalid credential `403`, runs non-root/read-only and emits redacted JSON request logs. No provider login, cloud mutation, deployment, DNS, UAT, Production or customer traffic occurred; PR review and merge remain. |
| WC-091 I1 disposable Demo readiness | MERGED - PR #424 as `7c11f9f2`; strict canonical environment rendering, catalog-derived secret bindings, anonymous provider projection, versioned/domain-separated identity HMAC, replica-scoped reset/reseed and real PostgreSQL replacement evidence are on `main`. No live Azure mutation occurred; real-account acceptance, I2 UAT persistence/recovery and I3 Production remain. |
| WC-092 Demo authentication repair | MERGED - PR #425 as `b73338ed`; modal-owned delayed loading, bounded provider projection, customer-safe copy, truthful provider states, persistent `403` recovery and privacy-safe BP denial diagnostics are on `main`. Real Google/deployed-rule acceptance, external hostname branding, cloud, DNS and provider mutation remain open or prohibited. |
| WC-093 public/auth experience finalization | IN-PROGRESS CHECKPOINT - Founder-approved public hero, four-professional orbit, exact WAOOAW branding and compact route-backed Login/Register dialogs are implemented on `ib/093/public-auth-experience-finalization` as `7c819c1d`. Full Web unit/lint/type/build gates, changed-component coverage, available Chromium/Firefox geometry, theme, RTL, reduced-motion, 200% text and axe checks pass. The exact Web and test images build, but inherited WC-078 qualification stops before its browser/scanner phase because `/not-a-public-route` returns 200 instead of the required 404; WC-093 did not change routing. Exact pushed-head prechecks, PR submission and Founder review/merge remain; no cloud, provider, deployment or Production action is authorized. |
| WC-095 agent employment lifecycle | PARTIAL / PORTAL, REVIEW, TRIAL AND HIRE REPOSITORY-QUALIFIED - Source head `09c6ad90` completes WC095-08/09 repository scope and repairs PR prechecks: generated-client review decisions, append-only actor-bound response/alert records, CE Evidence First with privacy-minimized reason hashes, exact replay/reconciliation and Operations reassessment relock. Docker evidence passes the full 792-test BP gate at 91.49% line / 80.01% branch coverage, 77 focused BP trial/Hire checks, 114 focused WBE trial/payment/promotion/workload/PostgreSQL checks, the exact 375-test Web type/lint/coverage gate, 7 focused Trial/Hire browser journeys and the 11-scenario WC-095 browser matrix. WC095-05B/SIM-095-23 remain `BLOCKED_EXTERNAL_INPUT`; WC095-07/SIM-095-16 remain blocked on absent governed runtime digests; active-work cancellation, erasure/legal-hold, exact-image, rollback, deployment, Production, approval and merge are not claimed. |
| WC-096 conversational customer portal | ENGINEERING QUALIFIED CHECKPOINT - Founder-authorized contract `d231a8ae` and milestones through `ecc846c7` deliver DF-001 through DF-009: canonical Marketplace routes/intents, disclosure and continuation, one persistent customer shell, accessible icon rail, authoritative My Agents cards, participant-bound durable Portal Guide interactions, generated channel-neutral clients and a contextual Guide/professional conversation dock. Docker evidence passes 714 BP tests, 356 Web tests, lint, TypeScript, production build, OpenAPI with zero errors and SQLFluff; complete PostgreSQL initialization and an application-role RLS probe show owner tenant `1` row and other tenant `0`. Desktop/360px WC-096 browser acceptance passes client navigation, dashboard, Guide continuity, relationship isolation, focus, accessibility and responsive geometry; professional conversation and authoritative offline reconciliation checks pass. Trial entitlement/payment remain explicit later lifecycle steps. No deployment, provider/mobile-device acceptance, customer traffic, UAT, Production, PR approval or merge is claimed. |
| WC-097 marketplace acquisition experience | ENGINEERING QUALIFIED CHECKPOINT - Milestone `17808018` replaces the compliance-led Marketplace card with an image-free WAOOAW offer, projects the canonical authenticated `/marketplace/{slug}` route from Business Platform, and keeps Trial/Hire review in the persistent customer shell with concise Terms and Privacy consent. Docker evidence passes 8 BP tests, 21 focused Web tests, TypeScript, lint, production build and OpenAPI with zero errors; six Chromium Trial/Hire journeys pass at 1440x900, 768x1024 and 360x800 with no horizontal overflow or serious/critical axe findings. DF-012 checkout/payment, deployment, UAT, Production, PR approval and merge are not claimed. |
| WC-098 customer registration readiness | ENGINEERING QUALIFIED CHECKPOINT - Work Contract `67759834` governs WC098-R01 through R10 / D01 through D09. Product commit `b9f738e1` and evidence `a756c9ea` establish issuer-plus-subject actor continuity, masked broker-verified email, deterministic dark/light preferences, disabled optional SMS, one registration title owner, safe typed recovery, actionable bounded provider retry and generated-client alignment. Docker evidence passes 734 BP tests, 361 Web tests, production build, lint, type, OpenAPI, audit and fixed high/critical image scan; eight Chromium checks pass at 360x800 and 1440x900 with no overflow or serious/critical axe findings. D09 exact Demo deployment/Azure correlation and Founder acceptance remain unclaimed; cloud mutation, customer traffic, SMS vendor/spend, PR approval and merge remain prohibited or Founder-reserved. |
| WC-099 post-Demo correction | ENGINEERING QUALIFIED CANDIDATE - Iteration 2 candidate `64cbce45` delegates Marketplace Trial/Hire to canonical lifecycle owners, enforces exact DMA offerability, requests fresh Google account selection, fails Guide startup/readiness for invalid cursor material, and repairs Guide/portal geometry. Iteration 3 milestone `3e86a9b5` adds fail-fast worktree/HEAD and Docker preflight, schema-v3 exact evidence binding, bounded non-runtime evidence reuse, and durable Platform IT Expert costly-run rules; 45 focused Docker tests and all 36 ledger rows pass. Existing product evidence includes 803 BP tests, 386 Web tests, 30 deployment tests, a 52-route production build and 29 WC-099 browser checks with 36 intentional project skips. R-014/R-020 remain blocked pending Founder merge and separately authorized work-component deployment; no cloud mutation, Demo acceptance, Production readiness, approval or merge is claimed. |
| WC-100 engineering validation efficiency | ENGINEERING QUALIFIED CANDIDATE - WC100-01 through WC100-04A are implemented on `ib/100/engineering-validation-efficiency`. Exact-head Docker qualification passes 61 focused ledger, orchestration, immutable-image, classifier and handoff tests with lint/format checks; current full PR CI remains authoritative. Hosted security/regression evidence, the 20-PR Shadow evaluation, candidate hosted timing, Founder review/merge and any WC100-04C activation remain open or Founder-reserved. |
| Production | PLAN ONLY - code-prepared; protected environments, authorized plan, traffic and final acceptance remain Founder-reserved |

### Checkpoint Context

- **Authority:** WC-076 and FA-052 evidence authorized the completed Demo/UAT work recorded in PR #371. No current authority for Production apply, DNS activation or customer traffic is inferred.
- **Execution contract:** `work-contracts/WC-076-goal006-phase3-execution.md`; backlog P3-EX01 through P3-EX11.
- **Cloud state:** Demo and UAT remain on the previously accepted exact-six release. Exact-seven is code-qualified but not deployed; Production remains plan-only.
- **Canonical route:** strategy is owned by `architecture/reference/pipeline/azure-deployment-topology.md`; operators enter through `.github/workflows/deploy.yaml`; detailed immutable evidence remains in `goals/GOAL-006-cloud-platform-finalization-evidence.md`.
- **Boundary:** no Production plan/apply, DNS activation, customer traffic, Platform Operations activation, final Goal acceptance, self-approval or self-merge without separate current authority.

## Authorization Boundary

GOAL-006 Phase 3 execution is authorized only inside FA-052: the named Azure tenant/subscription,
Central India, INR 15,000 one-time and INR 10,000 monthly ceilings, Demo/UAT and dark Production
boundaries, independent evidence gates and validity period. FA-052 does not authorize customer
traffic, material Production risk acceptance, Platform Operations activation, final Goal acceptance,
PR approval or merge. A failed constitutional, security, evidence, recovery, scope or cost gate stops
progression.

## Current Blockers

P3-EX11 offline readiness remains blocked until INST-009 accepts the Production edge, data, runtime,
recovery, cost and shared-state ownership inputs. Provider-backed planning also requires protected
Production GitHub environments and exact current-session Founder authority.
C-001 emergency-halt integration blocks Production apply and activation, which remain prohibited.
WC-084 Goal verification and Operations reassessment now pass local D-GOAL engineering gates; immutable
deployed-candidate and Founder acceptance remain. D-BILLING and D-IDENTITY were accepted by the
Founder on 2026-09-10 and remain queued as separate bounded implementation deliveries.
WC-085 brokered authentication is locally qualified, but trusted image publication, exact preview-client
deployment, real Google/Facebook account journeys and Founder visual acceptance remain open. Local
fixture and browser evidence is not provider acceptance or full WC-085 completion.
WC-085 full-schema rehearsal, stock reader/private TLS, recreated identity continuity, independent
downstream membership and browser account-switch qualification remain open; CB-009 tracks delivery.

## Next Authorized Action

Submit WC-099 Iterations 2 and 3 as one unmerged implementation PR for Founder review; do not deploy it to Demo without separate work-component authority. Submit WC-100 as an unmerged Shadow-mode PR for Founder review and hosted full-CI evidence; do not
activate selected PR execution before the required Shadow window and separate Founder approval.
Submit WC-097 for Founder review and merge. Submit the WC-085 brokered authentication follow-up for Founder review, trusted build and Demo
deployment before real-account acceptance. Submit the engineering-qualified WC-088 Customer
Multi-Agent And Skill Journey as a separate bounded PR. D-BILLING remains a separate queued
delivery; email login remains deferred.

Obtain INST-009 acceptance of the Production edge, data, runtime, recovery, cost and shared-state
ownership inputs required for P3-EX11 offline readiness. Do not activate the Production runner, run
a Production plan/apply, change DNS, or accept customer traffic without separate Founder authority.

## History And Evidence

- History through 2026-07-22: `constitution/PROJECT_STATE_ARCHIVE.md`.
- History from 2026-07-23 through WC-059 closure: git object
  `b0dbe9c^2:constitution/PROJECT_STATE.md` (the merged PR #265 head snapshot).
- WC-059 durable evidence: `work-contracts/WC-059-ae01-contract-payment-activation.md`,
  `goals/GOAL-005-wc059-implementation-evidence.md`, and reviews R-083/R-084.
- Schema-v2 governance record and independent review:
  `work-contracts/WC-061-project-state-v2-governance.md` and R-085.
- WC-060 readiness: `work-contracts/WC-060-goal005-ae01-continuity-evidence-stop.md`,
  `blockers/CB-004-wc060-canonical-contract-gaps-2026-08-11.md`, Amendment 9 in
  `goals/GOAL-005-execution-plan.md`, R-086, ACK-GOAL-005-INST-001-09, FA-041, and
  GOA-GOAL-005-INST-010-06.
- WC-060 implementation evidence and independent acceptance:
  `goals/GOAL-005-wc060-implementation-evidence.md` and R-087/R-088/R-089.
- WC-060 delivery closure: PR #268 merged to `main` as `95e0d91` after Founder approval.
- WC-062 implementation evidence and independent acceptance:
  `goals/GOAL-005-wc062-implementation-evidence.md` and R-096/R-097/R-098.
- WC-062 delivery closure: PR #273 merged by the Founder to `main` as `1a624d6` on 2026-08-12.
- WC-065 delivery closure: PR #278 merged by the Founder to `main` as `f28badc` on 2026-08-13;
  post-merge Docker regression and the PM delivery report passed.
- GOAL-006 Phase 2 delivery: PR #284 merged as `f52811436c900c2405aad871c43c88c073ae55fb`;
  post-merge closure PR #285 merged as `b0f1385a07ae02be1cbfd8b9b65f55acd498c65c`; WC-072
  and R-120 through R-126 are the durable evidence.
- GOAL-006 Phase 3 readiness: WC-073 and R-127 merged through PR #286 as
  `94701362d957fdc13d88bc7637c8b773a7cfb385`; WC-074 adds a planning-only enterprise delivery delta.
- GOAL-006 enterprise delivery addendum: WC-074 and R-128 merged through PR #287 as
  `bb511099ca5ff693ea538223e3779e4887421a99`; FA-050 stopped and FA-051 completed P3-WC01 read-only evidence.
- GOAL-006 cloud-only repository delivery: R-131 approved frozen SHA `199336c9`; PR #289 was merged
  by the Founder to `main` as `d49dad13fa3d7e9a670d847010f7b73e5612da51`. Post-merge execution
  backlog P3-EX01 through P3-EX11 is recorded in the P3-WC01 readiness evidence.
- Founder Commercial Governance formalization: PR #275 merged by the Founder to `main` as
  `2276ab2` on 2026-08-12; WC-064 remains ready for owner routing.
- Earlier completed work remains authoritative in its owning Work Contract, Goal, review,
  constitutional record, and repository history; it must not be copied back into this file.

---

## SPRINT_STATE_MACHINE
<!-- Machine-readable by autonomous-sprint.yaml. YAML-parseable block. -->
<!-- Edit ONLY the fields below. Do not alter the heading or fenced-block structure. -->
<!-- Task progress lives in work-contracts/WC-NNN-*.md, not here. -->

```yaml
autonomous_halt: false
platform_phase: IMPLEMENTATION
current_sprint: WC-034
sprint_status: DONE
branch: ib/014/wc034-f3-implementation
consecutive_failures: 0
tasks_done:
  - WC034-08
  - WC034-09
  - WC034-10
  - WC034-11
  - WC034-12
tasks_remaining: []
notes: |
  WC-034 F3 is complete and PR #254 merged as 8a1fcfa.
  This control block is retained for pipeline compatibility; it grants no new authority.
```

## Platform Delivery Summary

Last PM report: 2026-08-25
Platform Status issue: see GitHub Issues with label `platform-status`

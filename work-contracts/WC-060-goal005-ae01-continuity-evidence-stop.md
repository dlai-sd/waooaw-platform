# Work Contract 060 — AE-01 Omnichannel Continuity, Evidence, and Emergency Stop

**Goal:** GOAL-005 · **Epic stories:** AE-01-S09 and S10
**WC-034 Component:** F5 — Omnichannel Continuity (sole implementation contract)
**Office on execution:** Platform IT Expert (INST-010)
**Reviewer:** Security Architect (INST-007) + Data Architect (INST-006)
**WC-034 acceptance reviewer:** Enterprise Architect (INST-004) in an independent context
**Status:** IMPLEMENTATION COMPLETE — WC060-01 through WC060-09 complete; independent review pending
**Authorization:** FA-041, GOA-GOAL-005-INST-010-06, and ACC-GOAL-005-INST-010-06 authorize this session's implementation.
**Unification reviews:** R-073 architecture/product APPROVED; R-074 security/data APPROVED; R-075 constitutional APPROVED
**Track:** VERTICAL CUSTOMER OUTCOME
**Service scope:** BP (.NET), PR (Python), CE (.NET), web, ADR-023 Phone Identity Service integration

## Sprint Goal

Allow an authenticated customer to continue the same Employment Relationship across WhatsApp and web without identity, context, contract, authority, billing, or lifecycle drift; expose a tenant-safe Customer Evidence Window; and make Emergency Stop effective across all relationship sessions from the first trial interaction.

## Dependencies

WC-059 DONE; WC-014 PAAS/Emergency Stop and WC-037 Audit Sink DONE; D-04 accepted. Phone-only identity may perform low-risk conversation, but contract/payment/stop-release require configured step-up assurance.

## WC-034 F5 Contract Unification

Founder decision FA-037 selects WC-060 as the single implementation contract for WC-034 F5. WC-060 owns the complete continuity implementation and evidence package; successful completion of this contract, the F5 UX acceptance IDs, and the proportional F8 gate closes F5 without a second WC-034 implementation pass.

This unification does not waive WC-059 completion, per-session Founder implementation authorization, canonical owner contracts, generated-client compatibility, WC-060 security/data semantics, any adversarial CCT, C-076 coverage, C-080 Docker execution, or independent INST-007, INST-006, and INST-004 review. It does not authorize deployment, providers, F6-F8 feature implementation, or merge.

## Tasks

| Task | Scope | Model hint | Status |
|---|---|---|---|
| WC060-01 | Apply the exact Migration 22 blueprint in the D-06 Data Contract: independently authenticated channel bindings, continuity checkpoints, transport/participant acknowledgements, deduplication, tenant/relationship indexes, lifecycle/retention rules, and no ownership of relationship state. | reasoning | done — 22 Docker tests pass |
| WC060-02 | Implement ADR-023 and D-06 Security Contract controls: Meta HMAC, timestamp window, message deduplication, opt-in, 30-minute internal tenant-scoped phone JWT, relationship resolution, MPIN lockout, and Tier-4 portal proof for phone attach. An unknown phone may start a new evaluation but cannot attach to an existing relationship from phone possession or payload hints. | reasoning | done — 18 focused Docker tests pass |
| WC060-03 | Implement the canonical continuity endpoints and neutral Continuity Envelope from the D-06 Solution Contract. `ChannelContinuityService` prepares handoff, freshly authenticates/role-checks the target, binds its conversation, commits/reverts checkpoint, and returns the same relationship. Source remains active until target evidence commits. | reasoning | done — 10 continuity/controller Docker tests pass |
| WC060-04 | Extend PR session routing so multiple channel conversations resolve the same relationship and current authority while retaining separate delivery/session state. Offline/reconnect reauthenticates and re-evaluates pending intents; duplicate delivery cannot repeat a lifecycle outcome. | reasoning | done — 71 focused Docker tests pass |
| WC060-05 | Add the Evidence Reader endpoints in the D-06 Solution Contract and implement the D-06 Data/Security classification and access matrix. Query CE/Audit Sink through its approved read contract, enforce authenticated tenant + relationship + participant role, return only customer-visible material proof and authorized payload references, and provide evidenced short-lived export. | reasoning | done — CE/BP/migration Docker suites pass |
| WC060-06 | Build web relationship workspace and WhatsApp commands for timeline, evidence summary/export link, current authority/cost/trial state, and Stop. Distinguish transport acceptance from participant-observed acknowledgement and expose unresolved delivery honestly. | reasoning | done — web build, 6 UI tests, and 23 WhatsApp tests pass |
| WC060-07 | Bind Stop to the single AE-01 Employment Relationship: halt its evaluation/trial PAAS sessions, configuration, contract presentation, activation, and handoff within the existing latency budget; reject later consequential commands and show stopped state on every channel. Release is Tier-4 portal only, limited to active same-tenant `EMPLOYER`, freshly reauthenticated and explicitly confirmed with evidence linked to the originating Stop. Reconnect, conversation text, timeout, operator, or channel possession cannot release. AE-02 execution fan-out is deferred to AE-02 proof. | reasoning | done — 82 BP regressions, 24 WhatsApp tests, and 4 latency CCTs pass |
| WC060-08 | Add adversarial/integration CCTs for takeover, replay, confused deputy, assurance downgrade, cross-tenant query, out-of-order handoff, offline recovery, duplicate delivery, cross-channel Stop, unauthorized release, forged or replayed Neutral Continuity Envelope signatures, and full proposal-to-activation-to-handoff reconstruction. | auto | done — integrated BP/PR/CE/PostgreSQL Docker matrix passes |
| WC060-09 | Complete WC-034 F5 browser/generated-client acceptance for UX-CONV-03, UX-RES-02, and UX-CONT-01 through UX-CONT-06 at exact 360px and expanded viewports; run the proportional F8 accessibility, privacy, contract-conformance, coverage, lint, build, and regression gate; publish one integrated evidence package for independent INST-004 review. | auto | done — integrated F5/F8 evidence published |

### WC060-01 Evidence

Migration 22 and its EF Core ownership mapping are implemented. The focused Docker/Testcontainers
suite passes 22/22 checks covering first apply, idempotent reapply, composite foreign keys, forced
tenant RLS, checks and transition guards, append-only delivery acknowledgements, exact 15-minute
and 48-hour expiry, maintenance-role boundaries, replay arbitration, and concurrency uniqueness.

### WC060-02/03 Evidence

The WhatsApp boundary retains Meta HMAC verification, the five-minute timestamp window, message
deduplication, opt-in, privacy-safe phone HMAC, and 30-minute internal tenant token. Persistent
MPIN state now locks on the third failed attempt for 30 minutes. Internal phone attachment requires
fresh Tier-4 portal proof, an existing phone registration, an active same-tenant participant role,
and durable constitutional evidence; unknown-phone takeover attempts produce no relationship
mutation. The focused WhatsApp Docker suite passes 18/18 tests.

The canonical prepare/activate routes use authenticated server claims for tenant, participant,
channel, conversation, assurance, and carried internal envelope context. `ChannelContinuityService`
signs deterministic canonical JSON with HMAC-SHA256, persists the envelope hash, rejects divergent
idempotency and modified envelopes, rechecks current role/authority/Stop state, and commits target
binding only after evidence. Source binding remains active. The focused continuity and controller
Docker suite passes 10/10 tests; Migration 22 model and live PostgreSQL suites pass 26/26 tests.

### WC060-04 Evidence

Professional Runtime retains one durable Temporal execution per conversation and idempotency
identity while every BP assertion resolves the same server-authorized relationship context.
Reconnect reads durable workflow state, rechecks CE readiness, and reauthorizes the pinned
relationship, participant role, request hash, and Decision Space version before resuming events.
Current Stop, stale authority, denial, or CE uncertainty fails closed without executing a pending
intent. Existing replay arbitration prevents duplicate accepted requests from repeating workflow
mutation. The focused conversation execution Docker suite passes 71/71 tests.

### WC060-05 Evidence

CE implements the canonical internal `QueryEvidenceRecords` RPC and derives tenant scope only from
gRPC metadata. It returns only requested same-tenant Audit Sink proof fields, omits credential and
storage metadata, and suppresses payload references after erasure. The Audit Sink CCT passes 7/7.
BP collects opaque evidence IDs only from relationship-owned projections, resolves the caller's
active participant role from persistence, applies the evaluator/employer/relationship-manager
matrix, and keeps unknown, foreign, and unauthorized IDs privacy-safe. List/detail and export tests
pass 5/5. Exports freeze the current role-filtered document, canonicalize and SHA-256 hash it,
record constitutional evidence before persistence, replay identical idempotency, reject divergent
reuse, and issue a participant/role-bound HTTPS URL for exactly 15 minutes. Migration 22 model and
live PostgreSQL suites pass 26/26 with tenant-scoped durable export storage.

### WC060-06 Evidence

The established relationship workspace now loads the generated Evidence Reader projection, shows
customer-visible summaries, labels participant observation unresolved, and requests an evidenced,
time-limited export through an authenticated same-origin route. The relationship view retains the
authoritative timeline, trial/lifecycle state, authority version, commercial truth, and global
Emergency Stop access. WhatsApp `STATUS`, `TIMELINE`, `EVIDENCE`, `EXPORT`, and `STOP` presentations
direct customers to the secure authoritative workspace and distinguish transport acceptance from
durable participant acknowledgement. The generated TypeScript client was regenerated from BP
OpenAPI 1.7.0. Focused Jest suites pass 6/6, the WhatsApp Docker suite passes 23/23, and the
production Next.js build passes.

### WC060-07 Evidence

`RelationshipEmergencyStopService` discovers every non-terminal BP conversation execution for the
authenticated tenant and relationship, invokes the CE-owned Emergency Stop gRPC within its 200 ms
share, and projects the returned Stop evidence ID into `STOPPED_EMERGENCY`. Stop is legal from every
non-terminal AE-01 stage, idempotently preserves an existing Stop, and blocks configuration,
contract composition, activation, conversation execution, and handoff. The signed WhatsApp path
uses the same orchestrator and presents stopped state on later messages. Release requires an active
same-tenant `EMPLOYER`, Keycloak portal context, exact `TIER_4_PORTAL_FRESH` assurance no older than
five minutes, literal confirmation, non-empty justification, and evidence/correlation matching the
active originating Stop; release evidence includes `EMERGENCY_STOP_RELEASE:<evidence-id>`.
The generated Employment client exposes both Stop operations. The broad BP regression slice passes
82/82, WhatsApp passes 24/24, CE Emergency Stop latency CCTs pass 4/4, web Stop tests pass 6/6,
and the production Next.js build passes.

### WC060-08 Evidence

Continuity activation validates the signed envelope and target context before returning a committed
replay, so a forged replay cannot inherit prior success. It rebinds tenant, relationship,
participant, conversation, checkpoint, idempotency, freshness, role, authority, and assurance, and
rejects wrong-key/modified signatures, out-of-order activation, confused deputies, and assurance
downgrade without mutation. Exact committed replay returns its prior evidence. Focused BP denial,
replay, cross-tenant Evidence Reader, unauthorized Stop release, and full relationship-to-handoff
reconstruction CCTs pass 19/19. The integrated Docker matrix also passes PR offline/reconnect and
duplicate-delivery tests 71/71, Migration 22 live PostgreSQL replay/RLS/concurrency tests 22/22,
and CE tenant-scoped Evidence Reader plus Emergency Stop latency tests 5/5.

### WC060-09 Evidence

The generated browser client deterministically reproduces from BP OpenAPI 1.7.0 with no diff and
pins Employment handoff, Stop, release, and Evidence Reader operations. F5 Playwright acceptance
passes UX-CONV-03, UX-RES-02, and UX-CONT-01 through UX-CONT-06 at exact 360x800 and 1440x900,
with reviewed active/stopped baselines, zero serious/critical axe findings, and element containment.
The complete browser matrix passes 106 tests across Chromium, Firefox, WebKit, compact, expanded,
and intermediate projects with 19 intentional project-scope skips. Jest passes 89/89 at 94.63%
lines, lint is clean, and the production build passes. Final Docker regressions pass BP 309/309,
CE 83/83, and PR 153/153. The integrated attested evidence is published in
`goals/GOAL-005-wc060-implementation-evidence.md`.

## Required Inputs

`architecture/reference/product/omnichannel-continuity-contract.md` · `architecture/reference/product/ae01-business-boundary-contract.md` · `architecture/reference/product/ae01-solution-contract.md` · `architecture/reference/product/ae01-relationship-data-contract.md` · `architecture/reference/product/ae01-security-contract.md` · D-03 model/data semantics · AEEC-08 through AEEC-13 · ADR-003 · ADR-018 · ADR-023 · ADR-044 · BP and PR component specifications.

## Constitutional Compliance Tests

| CCT | Assertion |
|---|---|
| CCT-AE01-HANDOFF-01 | WhatsApp-to-web-to-WhatsApp preserves one relationship and unchanged contract/authority/billing state |
| CCT-AE01-HANDOFF-02 | Target-channel authentication must commit before authority-bearing handoff activates |
| CCT-AE01-HANDOFF-03 | Forged, modified, wrong-key, or replayed Neutral Continuity Envelope signature blocks activation with zero binding, relationship, authority, contract, billing, or lifecycle mutation |
| CCT-AE01-REPLAY-01 | Duplicate message/delivery/handoff returns prior outcome without duplicate mutation |
| CCT-AE01-TAKEOVER-01 | Phone/web takeover and confused-deputy attempts cannot access or mutate the relationship |
| CCT-AE01-DOWNGRADE-01 | Reduced channel assurance reduces capability and never protection |
| CCT-AE01-EVIDENCE-01 | Customer sees reconstructable own-tenant evidence and no other tenant data |
| CCT-AE01-STOP-01 | Stop on one channel halts all relationship sessions within C-001 budget |
| CCT-AE01-STOP-RELEASE | Reconnect, timeout, retry, operator, or low-assurance identity cannot release Stop |

## Definition of Done

- One authenticated customer traverses WhatsApp → web → WhatsApp with relationship and context intact.
- Evidence Window reconstructs discovery, trial, configuration, acceptance, payment, activation, handoff, and Stop with correct attribution.
- All takeover/replay/confused-deputy/downgrade/cross-tenant and forged/wrong-key/replayed continuity-signature cases deterministically deny or replay prior outcome with zero unauthorized mutation.
- Emergency Stop remains within the existing ≤250ms end-to-end constitutional floor and cannot be passively released.
- BP/PR/CE/web/integration/security suites, manifests/OpenAPI, DPDPA checks, and platform-state synchronization pass.
- UX-CONV-03, UX-RES-02, UX-CONT-01 through UX-CONT-06, and the proportional F8 acceptance matrix pass without a duplicate follow-on F5 implementation sprint.

## Validation Commands

```bash
docker compose --profile test-python run --rm test-runner-python pytest tests/professional-runtime/ tests/trust-layer/ -v
docker compose --profile test run --rm test-runner dotnet test tests/business-platform.Tests/ tests/constitutional-engine.Tests/
docker compose --profile test run --rm test-runner npm --prefix web test
docker compose --profile test run --rm test-runner npm --prefix web run build
```

## Boundaries

No AE-02 campaign execution, multi-agent behavior, provider connection, production deployment, or implementation authorization. No implementation starts without a future explicit Founder authorization.
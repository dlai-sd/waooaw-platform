# Work Contract 060 — AE-01 Omnichannel Continuity, Evidence, and Emergency Stop

**Goal:** GOAL-005 · **Epic stories:** AE-01-S09 and S10
**WC-034 Component:** F5 — Omnichannel Continuity (sole implementation contract)
**Office on execution:** Platform IT Expert (INST-010)
**Reviewer:** Security Architect (INST-007) + Data Architect (INST-006)
**WC-034 acceptance reviewer:** Enterprise Architect (INST-004) in an independent context
**Status:** IMPLEMENTATION-READY SPECIFICATION — fresh INST-005/INST-006/INST-007/INST-004/INST-002 readiness reviews approved; implementation authorization pending
**Authorization:** A future session requires explicit Founder authorization: “Authorize implementation of WC-060.”
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
| WC060-01 | Apply the exact Migration 22 blueprint in the D-06 Data Contract: independently authenticated channel bindings, continuity checkpoints, transport/participant acknowledgements, deduplication, tenant/relationship indexes, lifecycle/retention rules, and no ownership of relationship state. | reasoning | pending |
| WC060-02 | Implement ADR-023 and D-06 Security Contract controls: Meta HMAC, timestamp window, message deduplication, opt-in, 30-minute internal tenant-scoped phone JWT, relationship resolution, MPIN lockout, and Tier-4 portal proof for phone attach. An unknown phone may start a new evaluation but cannot attach to an existing relationship from phone possession or payload hints. | reasoning | pending |
| WC060-03 | Implement the canonical continuity endpoints and neutral Continuity Envelope from the D-06 Solution Contract. `ChannelContinuityService` prepares handoff, freshly authenticates/role-checks the target, binds its conversation, commits/reverts checkpoint, and returns the same relationship. Source remains active until target evidence commits. | reasoning | pending |
| WC060-04 | Extend PR session routing so multiple channel conversations resolve the same relationship and current authority while retaining separate delivery/session state. Offline/reconnect reauthenticates and re-evaluates pending intents; duplicate delivery cannot repeat a lifecycle outcome. | reasoning | pending |
| WC060-05 | Add the Evidence Reader endpoints in the D-06 Solution Contract and implement the D-06 Data/Security classification and access matrix. Query CE/Audit Sink through its approved read contract, enforce authenticated tenant + relationship + participant role, return only customer-visible material proof and authorized payload references, and provide evidenced short-lived export. | reasoning | pending |
| WC060-06 | Build web relationship workspace and WhatsApp commands for timeline, evidence summary/export link, current authority/cost/trial state, and Stop. Distinguish transport acceptance from participant-observed acknowledgement and expose unresolved delivery honestly. | reasoning | pending |
| WC060-07 | Bind Stop to the single AE-01 Employment Relationship: halt its evaluation/trial PAAS sessions, configuration, contract presentation, activation, and handoff within the existing latency budget; reject later consequential commands and show stopped state on every channel. Release is Tier-4 portal only, limited to active same-tenant `EMPLOYER`, freshly reauthenticated and explicitly confirmed with evidence linked to the originating Stop. Reconnect, conversation text, timeout, operator, or channel possession cannot release. AE-02 execution fan-out is deferred to AE-02 proof. | reasoning | pending |
| WC060-08 | Add adversarial/integration CCTs for takeover, replay, confused deputy, assurance downgrade, cross-tenant query, out-of-order handoff, offline recovery, duplicate delivery, cross-channel Stop, unauthorized release, forged or replayed Neutral Continuity Envelope signatures, and full proposal-to-activation-to-handoff reconstruction. | auto | pending |
| WC060-09 | Complete WC-034 F5 browser/generated-client acceptance for UX-CONV-03, UX-RES-02, and UX-CONT-01 through UX-CONT-06 at exact 360px and expanded viewports; run the proportional F8 accessibility, privacy, contract-conformance, coverage, lint, build, and regression gate; publish one integrated evidence package for independent INST-004 review. | auto | pending |

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
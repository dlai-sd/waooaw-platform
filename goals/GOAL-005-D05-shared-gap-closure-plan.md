# D-05 — Shared Gap Closure Plan

**Primary Institution:** INST-011 — Product Owner
**Architecture Reviewer:** INST-004 — Enterprise Architect
**Status:** CONTRIBUTED — pending final D-05 architecture review

## Institutional Records

| Institution | Acceptance | Contribution | Learning | Authorization |
|---|---|---|---|---|
| INST-011 | ACC-GOAL-005-INST-011-02 at 2026-08-08T15:00:00+00:00 | CR-GOAL-005-INST-011-02 at 2026-08-08T15:00:01+00:00; clarification CR-GOAL-005-INST-011-02-A1 at 2026-08-08T15:07:30+00:00 | LR-GOAL-005-INST-011-02 at 2026-08-08T15:07:31+00:00 | GOA-GOAL-005-INST-011-02 |
| INST-004 | ACC-GOAL-005-INST-004-04 at 2026-08-08T15:00:00+00:00 | CR-GOAL-005-INST-004-04 at 2026-08-08T15:00:01+00:00 | LR-GOAL-005-INST-004-05 at 2026-08-08T15:00:02+00:00 | GOA-GOAL-005-INST-004-04 |

All listed records use `goal_id` GOAL-005, their row Institution as `institution_id`, the listed ID as `record_id`, and their semantic `record_type` (`Acceptance Record`, `Contribution Record`, or `Learning Record`). Learning Records declare `constitutional_discovery: no` and `evolution_triggered: no`.

## G5-TRIAL-POLICY-01 Decision

| Policy field | Decision |
|---|---|
| Duration | 14 calendar days from activation or 3 completed trial sessions, whichever occurs first |
| Included capability | AE-01 discovery, disclosure, interview, context capture, trial-safe demonstration, evidence, and Emergency Stop visibility; no consequential external execution or AE-02 production work |
| Price/credit | One zero-price Trial Credit per `tenant_id + professional_type`; any paid variant discloses price before entry and preserves all rights/evidence |
| Output ownership | Customer retains inputs and customer-approved business artifacts; WAOOAW retains platform telemetry, constitutional evidence, and model/prompt internals |
| Expiry | Entitlement marker expires; no D-03 state is added. Further trial actions are denied; existing configuration/contract path, customer-authorized termination, and Emergency Stop remain available |
| Conversion | Explicit contract acceptance plus the D-03 four-part activation tuple |
| Cancellation/refund | Cancel anytime; zero-price trial has no refund; a paid variant refunds unused prepaid value within 7 business days |
| Qualifying customer | Verified authorized participant in the tenant, accepted terms, and no prior zero-price trial for the same `tenant_id + professional_type` |
| Customer-proof threshold | 10 completed live trial journeys, zero critical constitutional breaches, 100% evidence-chain completeness, and at least 80% reaching a contract decision; DMA is first proof, not the generic boundary |

Commercial values remain product policy and do not alter D-02, D-03, or D-04 architecture invariants.

## Wave 1 Closure Matrix

| Gaps | Specification evidence | D-06 checkpoint | Gate |
|---|---|---|---|
| PG-02 | All rights, limits, authority, skills, evidence, and price precede trial/commitment | CP-02 rights-first | Foundation |
| PG-03 | One relationship across replay/reconnect; zero duplicate mint | CP-03 identity continuity | Foundation |
| PG-04 | Stop reachable on every channel; customer-only evidenced release | CP-04 cross-channel stop | Foundation |
| PG-07 | Decision Space preview and scope confirmation distinct from approval | CP-07 configuration | Foundation |
| PG-08 | Complete trial policy; no consequential trial execution | CP-08 trial lifecycle | Foundation |
| PG-10 | Common rights plus domain schedule, accepted and authority-traceable | CP-10 contract composition | Foundation |
| PG-11 | Legal transition graph and deterministic activation replay | CP-11 lifecycle idempotency | Foundation |
| PG-01, PG-05, PG-06 | Conversational discovery, evidenced interview, and bounded business-language context | CP-01/05/06 | AE-01 exit |
| PG-09, PG-12, PG-13 | Mode/price visibility, exactly-once onboarding payment, and pre-degradation disclosure | CP-09/12/13 | AE-01 exit |
| PG-14, PG-15 | Authenticated non-duplicating handoff and reconstructable customer evidence | CP-14/15 | AE-01 exit |

Every gap is `SPEC_CLOSED` only when its customer scenario, deterministic pass/fail criteria, evidence method, closure metric, AEEC/D-03/D-04 trace, owner, dependencies, and risks are represented by this plan and its referenced foundation. D-06 must produce the checkpoint evidence; `SPEC_CLOSED` is not implementation or customer acceptance.

## R-038 Condition Closure

Out-of-order events carry causal marker and continuity checkpoint. A transition cannot commit without its predecessor; stale duplicates are non-mutating evidence; a missing predecessor produces unresolved state. D-06 injects out-of-order events and proves deterministic non-mutation.

For takeover, replay, confused deputy, downgrade, and cross-tenant access, D-06 must produce one adversarial scenario each. The only passing outcome is deterministic denial or prior-outcome replay, zero unauthorized mutation, and reconstructable actor/authority/correlation evidence.

## D-06 Entry Rule

D-06 may start only after architecture review confirms structural/value separation, all fifteen Wave 1 gaps are `SPEC_CLOSED`, and no D-02/D-03/D-04 invariant changed. D-06 finalization still requires all checkpoints and the Sujay DMA workshop evidence. No implementation is authorized.
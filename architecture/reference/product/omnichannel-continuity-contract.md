# GOAL-005 D-04 — Omnichannel Continuity Contract v1.0

**Status:** CONTRIBUTED — pending gate review
**Scope:** Specification-only continuity across WhatsApp, web, mobile, and future supported channels.

## Institutional Records

| Institution | Acceptance Record / time | Contribution Record / time | Learning Record / time | Authorization |
|---|---|---|---|---|
| INST-004 | ACC-GOAL-005-INST-004-03 / 2026-08-08T14:00:00+00:00 | CR-GOAL-005-INST-004-03 / 2026-08-08T14:00:01+00:00 | LR-GOAL-005-INST-004-04 / 2026-08-08T14:00:02+00:00 | GOA-GOAL-005-INST-004-03 |
| INST-007 | ACC-GOAL-005-INST-007-01 / 2026-08-08T13:40:00+00:00 | CR-GOAL-005-INST-007-01 / 2026-08-08T13:40:01+00:00 | LR-GOAL-005-INST-007-01 / 2026-08-08T13:40:02+00:00 | GOA-GOAL-005-INST-007-01 |
| INST-005 | ACC-GOAL-005-INST-005-01 / 2026-08-08T14:01:00+00:00 | CR-GOAL-005-INST-005-01 / 2026-08-08T14:01:01+00:00 | LR-GOAL-005-INST-005-01 / 2026-08-08T14:01:02+00:00 | GOA-GOAL-005-INST-005-01 |

Each listed item is respectively an `Acceptance Record`, `Contribution Record`, or `Learning Record`; each has `institution_id` equal to its row Institution, `goal_id` GOAL-005, `record_id` equal to the listed ID, `produced_at` equal to the listed time, and contributions/acceptances carry the listed `authorization_id`. All Learning Records declare `constitutional_discovery: no` and `evolution_triggered: no`.

## Ownership and Envelope

1. The Employment Relationship alone owns lifecycle state, authority, contract and activation checkpoints, and Emergency Stop state.
2. Channels own presentation, delivery, and session continuity only; conversations never own constitutional truth.
3. A neutral continuity envelope carries tenant, relationship, participant assertion, authority reference, conversation reference, causal/sequence markers, command purpose, idempotency intent, evidence linkage, and continuity checkpoint.
4. Channel-specific representation cannot redefine rights, authority, billing, or lifecycle meaning.

## Handoff and Security

1. Handoff preserves tenant and relationship identity and requires fresh target-channel participant authentication and current role/authority verification.
2. Source remains authoritative until target activation is evidenced. Failure preserves prior state and cannot merge roles, expand authority, or mutate contract, price, or lifecycle.
3. Tenant context is identity-anchored and cannot be overridden by payload hints. Cross-tenant access requires explicit constitutional authorization.
4. High-assurance actions cannot execute through downgraded assurance; fallback reduces capability, never protection.
5. Channel takeover, confused-deputy, replay, cross-tenant leakage, and downgrade threats must each have deterministic deny/evidence outcomes.

## Commands, Events, and Replay

- Command families: continuity handoff; consequential lifecycle intent; delivery assurance; Emergency Stop/release/termination.
- Event families: handoff prepared/authenticated/activated/reverted; transition proposed/committed/rejected; delivery accepted/observed/timeout/conflict; degradation/recovery/stop/release.
- Every consequential command binds tenant, relationship, participant, purpose, correlation, idempotency intent, and authority context.
- Materially identical replay returns the prior outcome. Divergent replay under the same intent yields explicit conflict and no mutation.
- Activation uniqueness remains the D-03 four-part tuple and cannot be redefined by a channel.

## Delivery Acknowledgement

Transport acceptance and participant-observed acknowledgement are distinct. A transition requiring participant observation cannot rely on transport acceptance alone. Timeout creates an explicit unresolved-delivery state, never silent success. Duplicate delivery cannot create a new lifecycle outcome.

## Emergency Stop, Offline, and Recovery

1. Emergency Stop has absolute priority over non-stop consequential commands and remains reachable during non-critical degradation.
2. Release requires explicit same-tenant customer authority linked to the originating stop evidence. Reconnect, timeout, retry, possession, or operator action cannot release it.
3. Offline state never mutates lifecycle. Reconnect reauthenticates, resolves the existing relationship, and re-evaluates pending intents under current authority and stop state.
4. Governance, evidence, identity, or tenant uncertainty halts consequential progression.
5. Delivery or handoff uncertainty preserves prior valid state. Recovery reuses correlation lineage and discloses degradation before consequential work resumes.

## Conformance Scenarios

1. One relationship survives WhatsApp-to-web-to-mobile handoff with no identity, authority, contract, price, or lifecycle mutation.
2. Every target channel reauthenticates the participant and records source-to-target continuity evidence.
3. Contract acceptance remains attributable; activation replay creates no duplicate activation or charge.
4. Emergency Stop on one channel is effective across all channels and cannot be passively released.
5. Offline/reconnect and delivery timeout preserve state and expose unresolved outcomes.
6. All consequential actions evidence actor, role, tenant, relationship, authority, and correlation.
7. Unauthorized cross-tenant access, downgrade, replay conflict, and takeover attempts produce zero successful consequential transitions.
8. Full proposal-to-activation-to-handoff evidence is reconstructable.

## Boundary

D-04 consumes AEEC-01 through AEEC-15 and D-03 without redefining them. It selects no API, schema, protocol provider, code, deployment, or release Work Contract. G5-TRIAL-POLICY-01 remains a D-05 closure item and D-06 blocker.
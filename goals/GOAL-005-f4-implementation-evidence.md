# GOAL-005 WC-034 F4 Implementation Evidence

## Contribution Record

| Field | Value |
|---|---|
| institution_id | INST-010 |
| goal_id | GOAL-005 |
| record_id | CR-GOAL-005-INST-010-04 |
| record_type | Contribution Record |
| produced_at | 2026-08-11 |
| authority | FA-036 current-session Founder implementation authorization; ACC-GOAL-005-INST-010-03 establishes the accepted executor context for preceding executable G-F4-10 |
| authorization caveat | No separately numbered GOA-GOAL-005-INST-010-04 is present. This record does not invent one; final INST-002 review must decide whether FA-036 satisfies Amendment 5's per-Institution GOA requirement. |
| contribution scope | WC-034 F4 dev/CI implementation: ADR-046 PKI and exact registry, PR and WBE mTLS private listeners and delegated-context verification, BP authenticated owner composition, owner projections, fourteen-operation BP facade, generated web client, six-family workspace, Docker evidence, and browser acceptance |
| excluded scope | Deployment, cloud Key Vault/certificate custody evidence, provider activation, production operation, customer proof, merge, and F5-F8 |

## Learning Record

| Field | Value |
|---|---|
| institution_id | INST-010 |
| goal_id | GOAL-005 |
| record_id | LR-GOAL-005-INST-010-03 |
| record_type | Learning Record |
| produced_at | 2026-08-11 |
| constitutional_discovery | no |
| evolution_triggered | no |
| improvement_signal | Transport provenance must originate in TLS state; cross-runtime delegation uses ECDSA P-256/SHA-256; owner failure must remain PARTIAL/UNAVAILABLE rather than being upgraded by BP. |
| residual risk | DMA has no authorized runtime owner source and remains explicitly UNAVAILABLE. Cloud rotation, revocation distribution, custody, migration, incident recovery, deployment, and customer proof require separately authorized evidence. |

## Environment Parity

| Property | Development | CI | Cloud |
|---|---|---|---|
| Trust domain | `waooaw.dev` | `waooaw.ci` | Required by ADR-046; not configured or claimed |
| Root custody | Ephemeral harness | Per-run ephemeral harness | Deferred to G-F4-13 deployment authorization |
| Leaf lifetime | 24 hours maximum | 2 hours maximum | ADR maximum specified; executable custody/renewal evidence absent |
| Exact URI SAN | Executable PKI tests | Executable PKI tests | Contract obligation only |
| mTLS minimum | TLS 1.2, client cert required | Same listener configuration | Contract obligation only |
| Audience/route/operation | Exact registry grants | Exact registry grants | Contract obligation only |
| Envelope lifetime/replay | 60 seconds/single use | 60 seconds/single use | Contract obligation only |
| Status | IMPLEMENTED | IMPLEMENTED | NOT CLAIMED |

## Owner And Customer Matrix

| Family | Owner implementation | BP translation | Customer state |
|---|---|---|---|
| Plan | BP placeholder only | No owner success fabricated | `UNAVAILABLE` |
| Attention | BP governance projection | Current empty authoritative list | `CURRENT` |
| Work | PR authenticated projection | Preserves `CURRENT`, `STALE`, `UNKNOWN`, `UNAVAILABLE`, or `BLOCKED` | Owner state or `UNAVAILABLE` |
| Results | DMA contract registered; no runtime owner source | No adapter call and no synthetic result | `UNAVAILABLE` |
| Usage and budget | WBE authenticated commercial projection | Relays owner actuals/forecast/threshold/version without recomputation | Owner state or `UNAVAILABLE` |
| Rights and controls | BP relationship state | Stop remains separately reachable | `CURRENT` |

Commands with incomplete multi-owner or CE/evidence paths remain `BLOCKED`; transport acceptance is never returned as business success.

## Executable Evidence

- BP: 175/175 tests; focused authenticated owner/signing tests 5/5.
- PR: 116/116 tests; focused workload identity, listener, and owner tests 27/27.
- WBE: 364/364 baseline plus 6 authenticated-verifier negative tests; focused remediation 9/9.
- Constitutional PKI/compatibility: 31/31; runtime boundary remediation 13/13.
- Web: 80/80 tests; lint and production build pass; desktop plus exact 360px Playwright 2/2.
- Canonical F4 compatibility manifest `PASS`; two pinned OpenAPI Generator 7.17.0 trees compile under strict TypeScript.

Evidence provenance is development/CI repository execution only. It is not deployment, production, customer, cloud-custody, migration, incident-recovery, or customer-outcome proof.
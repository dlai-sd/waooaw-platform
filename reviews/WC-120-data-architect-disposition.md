# WC-120 Data Architect Disposition

**Office:** Data Architect (INST-006)
**Review mode:** Founder-requested single-pass WC-120 specialist review and repair
**Date:** 2026-10-13
**Disposition:** **BLOCKED**

## Scope And Evidence

This bounded review covered WC-120 and its requirement/evidence ledger; the PR #498 enterprise
architecture at merged commit `4a4420af6ee132623d6b87eb3863d700e56c9b86`, especially §15,
§20, and §27; the PR #499 solution and API candidate at merged commit
`c2a1baf64cb3b2652ce29ed930ac4a60f14e73bb`, especially §§6, 12, 13, and 20;
and only the data-relevant existing Conversation Core, WC-114, and WC-115 surfaces pinned by
WC-120. No implementation, migration, provider/cloud state, or immutable constitutional record
was reviewed or changed.

Accepted profile and owner references used:

- `architecture/reference/api-specs/conversational-employment-specialist-profiles.yaml`, blob
  `9c7ccecd64791010f1ba15b69d9b8a128d466d66`, `data_profile`.
- `architecture/reference/components/conversation-core.md`, blob
  `1004255bbd01e3d10dd53a64a2b115ac059ad631`, §§1-3 and 5-8.
- `work-contracts/WC-114-conversational-employment-solution-contract.md`, blob
  `11ba639efa43d3288ba1eb39fd2e05308c42e6c0`.
- `work-contracts/WC-115-conversational-employment-implementation.md`, blob
  `337fcef0a51a4c2ef2ff72423a7afc64969d8914`, WC115-R077-R084.
- Prior input review `R-147`, blob `df8e78409c0cc7afc4177ab5f181971af46b3f2f`.
  Its original verdict remains `CHANGES REQUIRED`; PR #498 §27 is author remediation, not
  reviewer re-approval.

## Findings, Mappings, And Repairs

| Finding ID | WC120-R mapping | Finding and disposition | Repair / evidence |
|---|---|---|---|
| WC120-DA-001 | R004, R010, R012, R039 | **REPAIRED AND CLOSED.** Atomic boundaries, sequence, queue lease/retry/poison, and idempotency needed exact Data-owned values. | WC-120 §2.3 now fixes one scoped allocator, same-transaction sequence/idempotency/message/outbox, atomic inbox/effect, 60-second lease, 20-second heartbeat, no-jitter `min(2^(attempt-1)s, 300s)` retry, 12 attempts, `BLOCKED` poison, no silent discard, exact digests, unresolved non-expiry, and terminal-plus-30-day tombstones. Requirements and CE-FIT-08 bind 256-way races, crash boundaries, lease takeover, replay/conflict, and poison oracles. |
| WC120-DA-002 | R006, R014, R015, R039 | **REPAIRED AND CLOSED.** Payload/transcript lineage and derived-state invalidation needed exact controls. | WC-120 §2.3 fixes same-owner acyclic compare-and-swap supersession, exact source IDs/digests or sequence intervals, derivation versions, invalid-before-current-read behavior, erasable payload references, derivative erasure, and non-reconstructive evidence. R006/R014/R015 and CE-FIT-07/11 carry the direct oracles. |
| WC120-DA-003 | R014, R015, R023, R039 | **DATA PORTION REPAIRED AND CLOSED.** WhatsApp records lacked exact lifecycle mapping. | WC-120 §2.3 maps claims/tombstones to terminal plus 30 days; raw provider bodies and failed quarantine to 24 hours; delivery/opt-in/template facts to relationship closure plus seven years; accepted customer projections to closure plus 90 days; payload-free dead letters to terminal plus 30 days; exports to 24 hours; and authorized protected diagnostics to seven days. It also fixes hold technical fields, non-reactivation, erasure queue start within 24 hours, and platform-controlled deletion/invalidation within 72 hours. Legal basis/hold authority and material Founder acceptance are external dependencies, not missing Data values. |
| WC120-DA-004 | R023, R039 | **DATA PORTION REPAIRED AND CLOSED.** Numeric recovery targets and the recovery consistency group were absent. | WC-120 §2.3 and the matrix now propose Demo RPO/data loss 24h and RTO 8h; UAT 4h/4h; Production 15m/2h. Exact restore order, no-provider-egress environment, checksums, forced RLS, sequence/replay/lineage/source-expiry/projection oracles are bound. Founder acceptance of material cost/risk remains external. |
| WC120-DA-005 | R007, R029, R036, R037, R039 | **EXTERNAL PREREQUISITE.** One BP-owned durable conversation is mandatory, but the operation/schema/store crosswalk and corrected PR #499 read-position and six other wire findings are not Data-owned. | Chief Solution Architect and existing contract owners must record the crosswalk and corrected candidate. WC-120 §§2.1-2.3 and 9 stop `READY_FOR_STRATEGIC_PLAN`; Data does not select a successor operation or duplicate store. |
| WC120-DA-006 | R004, R007, R023, R039 | **REPAIRED AND CLOSED.** Tenant/RLS and migration controls needed implementation-grade boundaries. | WC-120 §2.3 fixes transaction-local server context, environment/tenant-complete keys and references, `ENABLE` + `FORCE RLS`, non-owner `NOBYPASSRLS` application/worker roles, schema-only migration authority, deterministic primary-key backfill batches of at most 1,000 rows, per-batch watermarks, seven-day old-reader compatibility, 24 hours of zero old-reader traffic before contraction, and no destructive down-migration. |

## Control Disposition

| Data concern | Result |
|---|---|
| Canonical conversation/message ownership | **CLOSED:** BP sole canonical owner; one durable conversation per Employment Relationship. Candidate crosswalk remains an external gate. |
| Transactions, sequence, inbox/outbox | **CLOSED:** exact allocator, atomic commits, ordering, lease/heartbeat/backoff/attempt/poison values, crash points, and 256-way concurrency oracle are fixed. |
| Idempotency and deduplication | **CLOSED:** distinct identity tuples, JCS/exact-byte digests, replay/conflict behavior, unresolved lifetime, and 30-day terminal tombstone are fixed. |
| Tenant isolation and RLS | **CLOSED:** environment/tenant-complete keys, transaction-local context, forced RLS, non-bypass roles, and bounded migration role are fixed. |
| Payload/transcript lineage | **CLOSED:** exact sources/versions, supersession, invalidation, erasable references, derivative erasure, and non-reconstructive evidence are fixed. |
| Retention, erasure, legal hold | **DATA CLOSED:** every record class has an exact Data lifecycle. Legal authority/basis and material Founder acceptance are named external gates. |
| Backup and restore | **DATA CLOSED:** consistency group, target values, restore environment/order, and direct invariants are fixed. Founder target acceptance and implementation evidence remain external/phase gates. |
| Migration and rollback | **CLOSED:** 1,000-row deterministic resumable batches, seven-day mixed-version window, 24-hour zero-old-reader gate, and non-destructive rollback are fixed. |
| WC-115 compatibility | **DATA CLOSED / EXTERNAL CROSSWALK:** WC-115 profile and R077-R084 remain controlling; CSA and contract owners must produce the exact candidate crosswalk. |

## Exact External Dependencies And Stops

1. **Legal:** accept or amend the legal basis and hold creation/release authority for
   `whatsapp_provider_transient`, `whatsapp_quarantine_transient`,
   `customer_export_transient`, and `protected_diagnostic_transient`. Data has fixed their
   technical periods and behavior; affected activation stops until Legal acceptance.
2. **Founder:** accept the material rights/cost/risk consequences of the lifecycle mapping and the
   proposed Demo 24h/8h, UAT 4h/4h, and Production 15m/2h recovery targets. Data has completed its
   proposal; recovery promotion and affected activation stop until acceptance.
3. **Chief Solution Architect plus existing BP/Core/WC-114/WC-115 contract owners:** complete the exact
   Core/WC-114/WC-115 operation/schema/store crosswalk and close the candidate read-position and
   six other PR #499 specification findings. This blocks `READY_FOR_STRATEGIC_PLAN`.
4. **Provider contract owner:** verify provider deletion/expiry capability and evidence states.
   WC-120 must report `UNRESOLVED`, never `ERASED`, until provider evidence exists.
5. **Platform IT Expert and Test Champion, only after implementation authorization:** create and
   run the planned sequence, crash, RLS, lifecycle, restore, migration, and CE-FIT artifacts in the
   approved Docker runners. Their pre-implementation absence is not a Data design blocker and no
   PASS is claimed now. The WC-120-referenced `scripts/validate_requirement_ledger.py` is also
   absent from the existing Docker runner and must be supplied or the contract must bind its
   accepted successor before the formal ledger gate can pass.
6. **Founder / provider / cloud / deployment authorities:** separately authorize any persistence
   activation, restore activation, teardown, provider action, cloud mutation, traffic, or
   Production change.

## Validation Evidence

- Docker runner YAML/digest validation parsed the requirement ledger and fitness matrix, proved
  unique requirement IDs, confirmed 44 requirements and 16 CE-FIT rows, verified the exact
  `data_architect_profile` values, and matched the contract SHA-256 to `contract_digest` — **PASS**.
- `git diff --no-index --check /dev/null <file>` over the WC-120 contract, requirement ledger,
  fitness matrix, and this disposition reported no whitespace errors — **PASS**.
- Pinned source blobs for the accepted specialist profile, WC-114, and WC-115 were present and
  readable at their recorded identities — **PASS**.
- The formal WC-120 validator command is **BLOCKED** because
  `scripts/validate_requirement_ledger.py` is not present in the existing Docker test runner.
  No host Python, virtual environment, or ad hoc host substitute was used.

## Final Disposition

**BLOCKED — NO OPEN DATA-OWNER FINDINGS.** WC120-DA-001, -002, -003, -004, and -006 are repaired
and closed with exact controls, values, targets, and oracles. WC120-DA-005 and the dependencies above
are concrete Legal/Founder/CSA/provider/implementation-phase gates owned outside the Data Architect's
Decision Space. This is not Founder or Legal acceptance, implementation authorization,
deployment/activation authority, PR approval, or merge approval.

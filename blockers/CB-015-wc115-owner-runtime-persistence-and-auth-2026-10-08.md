# CB-015 - WC-115 Owner Runtime Persistence And Authentication

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-015` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-08` |
| Status | **RESOLVED - OWNER PERSISTENCE AND AUTHORIZATION QUALIFIED** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-115 Stages WC115-01, WC115-02, WC115-05 through WC115-07; WC115-R007, R010, R021-R023, R037, R050, R057-R060, R077-R080, R083, R102 and R108 |
| Constitutional basis | C-023, C-026, C-059, C-063, C-079, C-080; ADR-046; ADR-051; WC-115 Sections 2.2, 7.1-7.3, 7.5, 8, 13 and 14 |
| Resolution authority | Platform IT Expert implementation within the accepted WC-114 candidate.2 specialist profile; no new Founder policy value is required |

## Founder Scope Disposition

The Founder directed that WC-115 remain free of DMA production changes. Agent-specific domain
semantics requirements WC115-R024-R026 are therefore `FOUNDER_RESERVED` for a separate
agent-specific PR. Generic WAOOAW adapter contracts, handlers, fail-closed unavailability, security
boundaries and cross-profession fixtures remain in scope for WC-115.

## Blocking Facts

The WC-115 implementation author review found:

1. `professional.employment_execution_records`,
   `ai_runtime.employment_patch_proposals` and
   `billing.employment_eligibility_versions` exist with forced RLS and owner grants, but the PR,
   AIR and WBE candidate runtime services configure process-memory stores instead of those canonical
   owner stores.
2. AIR proposal authorization uses a shared bearer secret and caller-supplied workload URI rather
   than the accepted mTLS peer identity plus signed delegated envelope. AIR therefore cannot derive
   the server-trusted tenant identity required by its canonical table.
3. Generic adapter employment routes use the same shared bearer-secret pattern, while BP signs the
   accepted delegated envelope. The live caller and provider authentication contracts do not match.
4. The workload registry has no AIR workload identity or PR-to-AIR employment proposal route grant.
5. Existing unit and generated-client tests exercise owner logic and HTTP shapes but do not prove
   restart-safe owner persistence or a live signed-envelope provider boundary for AIR and the
   generic adapter.

These are platform-side WAOOAW gaps. They require no DMA-specific production code.

## Repairs Completed During Review

- BP source objects now match the candidate.2 schema, including closed owner/state values,
  `limitation`, and validated freshness windows.
- Calendar commitments now validate IANA zone, local time, UTC instant, offset, fold, DST gaps and
  ambiguity, and the closed tolerance-policy identity.
- Readiness, operations, phase, plan, item, blocked-effect, progress and available-command
  structures now enforce their closed candidate enums and nested schemas.
- The .NET dependency scanner now isolates referenced project artifacts without corrupting generated
  client restore state.
- WC115-R024-R026 explicitly record the Founder-reserved separate agent-specific PR boundary.

## Gate Effect

- Final aggregate Docker qualification must not start while this blocker is open.
- WC115-R071 and WC115-R072 cannot truthfully become PASS.
- No exact-head author-review PASS or Founder-ready PR may be created.
- The candidate capability remains disabled by default. No activation, deployment or customer
  traffic is authorized.

## Required Resolution

1. Add AIR to the workload-identity registry and add the exact PR-to-AIR candidate route grants.
2. Make AIR and generic adapter routes verify mTLS peer identity and the exact signed delegated
   envelope, including route, operation, audience, digest, tenant, relationship, correlation and
   replay binding.
3. Wire PR, AIR and WBE candidate owner records to their accepted PostgreSQL tables with
   transaction-local server-derived tenant context.
4. Prove durable reservation/replay, restart reconciliation, append-only history, RLS denial,
   wrong-workload denial and provider/caller contract compatibility in Docker.
5. Rerun the affected PR, AIR, WBE, adapter, PostgreSQL, security and cross-owner gates before final
   qualification.

No repair may reintroduce a shared secret as workload identity, accept tenant identity from request
payload, represent process memory as durable owner truth, touch DMA production semantics, weaken a
threshold or mark the blocked requirements PASS from schema-only evidence.

## Resolution

The Platform IT Expert completed the authorized WAOOAW-side repairs:

- AIR and WBE use their PostgreSQL owner tables with transaction-local, server-derived tenant
  context; AIR idempotency and proposal reconciliation survive process restart.
- AIR authenticates the exact PR mTLS peer and signed delegated envelope with route, operation,
  audience, digest, tenant, relationship, correlation and replay binding.
- PR is registered as a delegation signer, AIR has an exact workload identity, and the two
  PR-to-AIR proposal routes have exact grants.
- PR durably accepts conversation execution before dispatching the AIR proposal, reconciles the
  immutable result and emits the typed non-authoritative proposal card.
- Generic adapter employment routes require an injected authorization boundary and fail closed
  while WC115-R024 through WC115-R026 remain Founder-reserved.
- Docker component, security, PostgreSQL, parallel catalog and final release-qualification gates
  pass on candidate commit `0c97038fd10c9963edc826a3cfeb6718937154e4`.

No DMA production semantics, activation, deployment or customer traffic was introduced. The
immutable evidence summary is `validation/evidence/wc115/qualification.json`.

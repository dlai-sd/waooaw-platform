# Identity Security Data Contract

**Authority:** WC-103; Founder-requested Data Architect one-pass edit review, 2026-09-20
**Status:** PROPOSED FOR FOUNDER REVIEW - IMPLEMENTATION NOT AUTHORIZED
**Constitutional basis:** C-002, C-005, C-007, C-023, C-026, C-027, C-063; ADR-003, ADR-009, ADR-011

## Ownership And Separation

Operational identity-security events belong to the platform security function and use a dedicated
`institutional.identity_security_events` append-only relation. They are not Customer Evidence,
Professional Experience or Constitutional Audit Ledger records. Constitutional decisions continue
to write `constitutional.*` evidence under C-023. The two record classes may share one opaque
correlation ID but no query path or foreign key merges their ownership.

Active session state uses `business.identity_sessions` because it is revocable customer-account
operational state, not immutable evidence. Session rows may change state through narrowly granted
stored operations. Revocation appends a separate immutable security event before the revocation
operation reports success.

## Logical Event Schema

Each `identity_security_events` record contains:

- `event_id` UUID and `occurred_at` UTC timestamp;
- opaque `correlation_id` and optional keyed `actor_ref`/`session_ref`;
- environment, event type, provider class, outcome and stable reason code;
- assurance class, source boundary and schema version;
- optional approved rotating keyed network/device risk references; and
- `recorded_at` UTC timestamp and writer service identity.

The event taxonomy covers authentication start, provider handoff, callback success/failure, session
establishment, registration start/completion/failure, refresh success/failure, authorization denial,
logout request/completion/failure, account switch, session expiry and single/all-session revocation.
An idempotency key derived from source boundary plus source event identity prevents duplicate writes
without updating an existing row. Corrective interpretation appends a superseding event.

## Session Projection

Each `identity_sessions` row contains an opaque session ID, keyed account/actor reference, issued,
last-seen, absolute-expiry and revoked timestamps, assurance class, provider class, coarse customer-
safe device label and revocation reason. No token or credential is stored. The customer projection
shows only information needed to recognize and revoke a session; it never exposes internal event,
tenant, IP or provider-subject identifiers.

Revoke-all uses an account-scoped revocation generation or equivalent transactionally ordered value.
Refresh and callback completion must compare the current generation before committing session state.
This makes revocation win concurrent refresh/callback races without deleting session history.

## Database Controls

- Event writer roles receive `INSERT` only; investigator roles receive bounded `SELECT`; no runtime
  role receives `UPDATE`, `DELETE` or `TRUNCATE` on committed events.
- Database triggers or privileges reject mutation and direct insertion of forbidden payload fields.
- Session and event access is tenant/account scoped through restricted functions and RLS where a
  customer boundary exists; no public operation accepts tenant ID.
- Connection-pool tests prove transaction-local identity/tenant context is reset between requests.
- Retention is policy-driven by event class and legal purpose. Expiry uses partition retirement or
  cryptographic erasure under an approved retention process, never ad hoc row mutation. A legal hold
  suspends expiry without changing committed records.
- Backups, replicas and exports inherit encryption, access, retention and deletion controls.

## Data Acceptance

1. Migration rehearsal proves schema, constraints, grants, triggers/RLS, rollback and forward-only
   event compatibility on real PostgreSQL.
2. Application roles cannot update/delete/truncate events or read another account's sessions.
3. Duplicate delivery creates one effective event; correction appends rather than mutates.
4. Revoke-one/all races with refresh and callback completion converge deterministically.
5. Retention and legal-hold tests prove approved expiry without weakening immutable constitutional
   evidence or erasing active security investigations.
6. Forbidden-data fixtures and scans prove secrets, raw PII and authorization material are absent.

Physical names may change only through Data Architect amendment before implementation; Runtime may
not invent an alternative ownership zone, mutable log table or cross-ledger join.
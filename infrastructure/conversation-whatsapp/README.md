# WC-120 Conversation And WhatsApp Operations

This directory contains repository-only, default-off environment readiness records. It does not
authorize provider access, cloud or DNS mutation, callback registration, traffic, deployment,
activation, teardown, recovery activation, Production action, approval, or merge.

## Environment readiness

Validate the three manifests in the repository Docker test runner:

```text
docker compose --profile test-python run --rm test-runner-python \
  python scripts/validation_control/validate_wc120_environment_manifests.py
```

The validator requires distinct Demo, UAT, and Production references, split secret authorities,
environment-specific callback hosts, no complete telephone value, no restore routing, no provider
egress, and all activation flags off. Production must retain
`PRODUCTION_PENDING_PURCHASE`.

Before any separately authorized activation, inject immutable policy/configuration versions and
protected provider bindings for exactly one environment. Never copy another environment's app,
WABA, recipient, secret, workload, callback, data, media, telemetry, template, or deployment
authority.

## Expand and migrate

1. Keep `Wc120Conversation.Enabled`, callback acceptance, and dispatch off.
2. Apply the additive PostgreSQL init set including
   `infrastructure/postgres/init/36-wc120-conversation-whatsapp.sql`.
3. Back up the complete WC-120 consistency group.
4. Run `infrastructure/postgres/operations/wc120-backfill.sql` repeatedly with an environment and
   batch size no larger than 1,000 until both watermarks are `COMPLETE`.
5. Prove sequence, environment, idempotency, claim, lineage, RLS, and policy/context snapshot
   invariants before enabling any reader.
6. Enable only the shared conversation projection for generated-client qualification. Callback
   acceptance and dispatch remain separately gated.

The migration is forward-only and restartable. It never removes legacy columns, history, evidence,
or payload lineage. Legacy messages receive explicit `STALE` legacy context/policy snapshots; they
are not represented as current context.

## Isolated restore

Restore only under separate recovery authority into a non-routable environment with:

- callback acceptance off;
- dispatch and template use off;
- provider egress off;
- no provider, callback, DNS, or Production credential;
- temporary environment-specific workload and encryption authority.

Restore this consistency group in order:

1. schema and migration watermarks;
2. canonical conversation/messages and sequence state;
3. idempotency, provider claims, inbox/outbox, leases, and unresolved outcomes;
4. context/profile lineage and data-right orchestration;
5. payload references and payloads;
6. delivery observations and deterministic projections;
7. summaries, caches, Stop latches, and operational signals.

Run `infrastructure/postgres/operations/wc120-restore-verification.sql` in the isolated database.
Any invariant mismatch or provider egress fails qualification immediately and keeps the restore
non-routable. Do not activate a restored environment without new identity, consent, template,
policy, Stop, schema, RLS, and binding evidence plus separate Founder authority.

Accepted recovery limits are:

| Environment | RPO | RTO |
|---|---:|---:|
| Demo | 24 hours | 8 hours |
| UAT | 4 hours | 4 hours |
| Production | 15 minutes | 2 hours |

## Application rollback

1. Disable callback acceptance and dispatch for the exact environment.
2. Stop new leases and reconcile every `DISPATCHING` or `UNRESOLVED` provider outcome.
3. Preserve claims, tombstones, Stop latches, delivery observations, evidence, and additive schema.
4. Under separate rollback authority, run
   `infrastructure/postgres/operations/wc120-rollback.sql` with the environment and rollback
   evidence identifier. The script fences only pending work; it does not fabricate outcomes or
   delete history.
5. Restore the prior compatible application image only after proving its schema compatibility.
6. Never restore revoked credentials or reverse provider, DNS, customer-visible, or constitutional
   effects.

## Demo teardown

Demo teardown requires separate Platform/provider/Data authority. First disable callback acceptance,
then reconcile or isolate unresolved work, revoke temporary authority, erase eligible payloads,
retain required tombstones/evidence, and prove UAT and Production bindings changed by zero. The
repository manifests remain default-off records and are not evidence that teardown occurred.

## Operational response

Payload-free signals cover queue age, unresolved outcomes, dead letters, media rejection, Stop
evidence reconciliation, recovery, privacy, isolation, and Production-dark violations.

- Queue age over 120 seconds or unknown outcome over 15 minutes: page within 5 minutes and suspend
  unsafe retry while identity is uncertain.
- Dead letter over 15 minutes: notify within 5 minutes; at 30 minutes, page.
- Any privacy, isolation, Production-dark, restore-egress, or Stop hard-ceiling event: detect within
  1 minute, page within 5 minutes, acknowledge within 10 minutes, and fence within 30 minutes.
- Missing signal or alert delivery is a failed oracle, never success by silence.

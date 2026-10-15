# CB-018 - WC-123 Demo And UAT Capacity Inputs

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-018` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-14` |
| Status | **CLOSED** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-123 AUTH-WC-01 completion and AUTH-WC-02 entry |
| Constitutional basis | C-023, C-059, C-080; CSA-AUTH-001 Section 12.7; WC-123 Sections 2.2, 7.1, and 15 |
| Resolution authority | Chief Platform Architect for accepted capacity inputs; Platform IT Expert for implementation and proof |

## Resolution

The Chief Platform Architect accepted versioned profile `wc123-auth-capacity-v1` at
`architecture/reference/components/authentication-authorization-capacity-profile.v1.yaml`.
Demo and UAT reference that exact profile from their source environment manifests, and their
rendered manifests carry the same reference.

The accepted database inputs are `max_connections=100`, migration/operations reserve `20`, and
per-replica Web session pool `5`. Demo retains its phase2 maximum of `1`, producing
`1 * 5 + 20 = 25 <= 80`. UAT accepts the workload module default maximum of `10`, producing
`10 * 5 + 20 = 70 <= 80`. PgBouncer transaction pooling remains the accepted ADR-027 architecture.

The same profile now binds all request, refresh, callback, and lifecycle queue limits; global and
per-principal concurrency including exactly one refresh per family; all six dependency timeouts;
the retained ACA threshold of 30 concurrent requests per replica; typed overload and retry bounds;
and the existing INR 10,000 monthly ceiling independently for Demo and UAT.

## Evidence

- Catalog `spec-lint`: PASS, namespace `wc109-9fad5065774e6d4a`.
- Catalog `test-web`: PASS, 555 tests, namespace `wc109-2f71af4330590d7f`.
- Catalog `test-dotnet:business-platform`: PASS, 1,086 tests at 90.00% line and 80.37% branch,
  namespace `wc109-0cfe5b9ea458c91d`.
- Catalog `wc123:impact-manifest`: PASS, 5 tests, namespace `wc109-378dbdb6b584f904`.
- Repaired catalog `wc123:impact-manifest`: PASS, 9 tests, namespace
  `wc109-213699c8b0447fe4`.

The repair adds deterministic profile, manifest, equation, timeout, queue/concurrency, ACA, and cost
tests to `tests/pipeline/test_wc123_impact_manifest.py`. The final catalog result is recorded below.

## Gate Effect

- AUTH-WC-01 capacity acceptance is complete.
- The capacity blocker to AUTH-WC-02 is removed. Separate Founder authorization is still required
  before implementation begins.
- No Web, Business Platform, OpenAPI, migration, generated, provider, cloud, deployment, traffic,
  activation, Production, approval, or merge change has started.

## Durable Evidence

Future agents do not need to infer or copy these values from WC-123 prose:

1. the architecture value set is named and versioned in one accepted profile;
2. Demo and UAT environment contracts reference that profile explicitly;
3. rendered consumers are checked against their source manifests;
4. the impact manifest records exact sources and both calculated equations; and
5. focused tests fail on profile incompleteness, source drift, equation failure, timeout inversion,
   unbounded queues/concurrency/retries, ACA mismatch, or cost-ceiling mismatch.

No provider or cloud mutation, deployment, traffic, activation, Production action, approval, merge,
AUTH-WC-02 implementation, or `src/` change was performed.

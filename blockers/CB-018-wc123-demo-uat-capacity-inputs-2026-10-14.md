# CB-018 - WC-123 Demo And UAT Capacity Inputs

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-018` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-14` |
| Status | **OPEN** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-123 AUTH-WC-01 completion and AUTH-WC-02 entry |
| Constitutional basis | C-023, C-059, C-080; CSA-AUTH-001 Section 12.7; WC-123 Sections 2.2, 7.1, and 15 |
| Resolution authority | Chief Platform Architect for accepted capacity inputs; Platform IT Expert for implementation and proof |

## Blocking Fact

AUTH-WC-01 has bound all 48 requirements, accepted source digests, current authority paths, exact
planned change surfaces, generated consumers, data/secret ownership, migration/rollback boundaries,
and catalog-controlled baseline evidence in `work-contracts/WC-123-impact-manifest.yaml`.

The repository supplies the accepted 80-percent database-connection ceiling and Demo Web maximum of
one replica. It does not supply accepted Demo and UAT values for:

- application database connection limit;
- migration and operations connection reserve;
- per-replica Web session pool;
- request, refresh, callback, and lifecycle queue limits;
- global and per-principal concurrency limits;
- pool-acquisition, lock, statement, BP membership, Redis, and identity-provider timeouts; or
- the corresponding environment cost input.

UAT does not currently bind a Web maximum replica value in the environment source either. Therefore
`max_replicas * per_replica_pool + reserve <= 80% * connection_limit` cannot be calculated or
qualified without inventing architecture and operating values.

## Evidence

- Catalog `spec-lint`: PASS, namespace `wc109-9fad5065774e6d4a`.
- Catalog `test-web`: PASS, 555 tests, namespace `wc109-2f71af4330590d7f`.
- Catalog `test-dotnet:business-platform`: PASS, 1,086 tests at 90.00% line and 80.37% branch,
  namespace `wc109-0cfe5b9ea458c91d`.
- Catalog `wc123:impact-manifest`: PASS, 5 tests, namespace `wc109-378dbdb6b584f904`.

These baselines establish current behavior and manifest integrity. They do not prove the missing
capacity equation or authorize placeholder defaults.

## Gate Effect

- AUTH-WC-01 remains incomplete.
- AUTH-WC-02 and every dependent component remain blocked.
- No Web, Business Platform, OpenAPI, migration, generated, provider, cloud, deployment, traffic,
  activation, Production, approval, or merge change has started.

## Required Resolution

The Chief Platform Architect must accept exact Demo and UAT values for every missing input above,
including the cost envelope and source-of-truth environment fields. Platform IT Expert will then:

1. bind them in the accepted environment-manifest contract;
2. calculate and test the 80-percent database-connection ceiling;
3. add bounded overload, queue, timeout, cold-start, reset, restart, and recovery selectors; and
4. rerun `wc123:impact-manifest` before declaring AUTH-WC-01 complete.

Inventing values, relying on PostgreSQL defaults, copying unrelated workload limits, or postponing
the capacity proof until deployment is prohibited.

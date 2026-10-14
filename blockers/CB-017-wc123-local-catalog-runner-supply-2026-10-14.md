# CB-017 - WC-123 Local Catalog Runner Supply

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-017` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-14` |
| Status | **OPEN** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-123 AUTH-WC-01 baseline and all dependent implementation components |
| Constitutional basis | C-023, C-059, C-080; WC-123 Sections 2.1, 7.1, 11, and 15 |
| Resolution authority | Platform IT Expert for the repository validation paved path |

## Blocking Facts

WC-123 implementation was explicitly authorized for the current session. Process-control version
`wc100-r033-v1`, all declared process-source digests, branch ancestry, Docker readiness, and the
48-row WC-123 requirement ledger pass at accepted head
`2cae98c98821e687f643e436872f18013ed65ca2`.

AUTH-WC-01 then invoked the repository-owned `spec-lint` gate through
`scripts/validation_control/local_catalog_gate.py` inside `test-runner-python`. The gate stopped
before specification execution on two reproducible runner-supply failures:

1. The first execution preflight rejected `/var/run/docker.sock` because the Compose invocation had
   not propagated the host socket GID into the runner.
2. After supplying the repository-declared `DOCKER_GID`, socket preflight passed, but local runner
   resolution failed because `test-runner-python` does not contain the Docker CLI required by
   `local_catalog_gate.py`.

Both failures are classified `RUNNER`. No specification, product, test, migration, generated,
provider, cloud, deployment, or traffic action ran.

## Gate Effect

- AUTH-WC-01 cannot record an authoritative baseline.
- AUTH-WC-02 through AUTH-WC-07 cannot start because they depend on AUTH-WC-01.
- Direct `docker compose run`, host-language tests, or another non-catalog command cannot substitute
  for authoritative PASS evidence.
- Release Qualification remains OFF, but that waiver does not waive focused or milestone catalog
  execution.

## Required Resolution

Provide one repository-owned Docker launcher or supplied runner that:

1. executes `local_catalog_gate.py` without host Python;
2. includes the Docker CLI required for nested runner supply;
3. maps the Docker socket with its exact host GID;
4. mounts the selected linked worktree and Git common directory at their original absolute paths;
5. preserves writable, host-visible evidence directories; and
6. passes the static execution preflight before building or running a gate.

After repair, rerun the exact `spec-lint` focused gate once. Do not bypass the executor, weaken the
preflight, install host tooling, or treat a direct test command as authoritative evidence.

# CB-016 - WC-123 Accepted Input Digest And Keycloak Lifecycle Decision

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-016` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-14` |
| Status | **OPEN** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-123 implementation intake and AUTH-WC-05 through AUTH-WC-07 |
| Constitutional basis | C-023, C-059, C-065, C-080; WC-123 Sections 2.1, 2.6, 4, 15, and 16 |
| Resolution authority | Chief Solution Architect and Founder for AUTHZ-GATE-01; Founder for accepted-input amendment |

## Blocking Facts

The Founder authorized bootstrap and WC-123 implementation in the current session. The selected
worktree is clean on `ib/123/authentication-authorization-runtime` at
`787c428841743ab2c8c112e65397e6937b35a772`, with `origin/main` as an ancestor. Process-control
version `wc100-r033-v1` and all three declared process-source digests pass.

The repository Docker runner validates all 48 WC-123 requirement rows and the complete Work Contract
digest. The accepted input package is nevertheless internally stale:

| Input | Ledger SHA-256 | Actual SHA-256 |
|---|---|---|
| `work-contracts/WC-123-authentication-authorization-implementation.md` | `f1ded2acc5093395bbae1ddb1df2775e32a6b9c1c4abe9e2861c3e827cc69f99` | `f1ded2acc5093395bbae1ddb1df2775e32a6b9c1c4abe9e2861c3e827cc69f99` |
| `architecture/reference/components/authentication-authorization-simplification-solution-contract.md` | `16afccde6187626f8e12769348b7bb4ad0f8bd2447f05ab781864eed5449ada7` | `6d88ab96132bf0728ad7c92cd89ed58413f315714f53f0350fb483fe85bf384a` |

The accepted solution contract and WC-123 also leave `AUTHZ-GATE-01` unresolved. They do not name an
accepted stock-Keycloak lifecycle proof/mutation interface, supported pinned-version behavior,
least-privilege credential and owner, private route, idempotency/read-back semantics,
ambiguous-outcome compensation, upgrade test, or customer-visible consequence.

## Gate Effect

- No WC-123 story has been declared `START`.
- No source, Web, generated, migration, dependency, build, provider, cloud, deployment, traffic, or
  activation change has occurred.
- The stale solution digest prevents the required exact accepted-source freeze.
- `AUTHZ-GATE-01` blocks provider link, unlink, recovery, and principal-rebinding mutation in
  AUTH-WC-05 and therefore blocks dependent AUTH-WC-06, AUTH-WC-07, and WC-123 completion.
- The current-session implementation authority does not waive either accepted-input freshness or
  the architecture decision gate.

## Required Resolution

1. Accept and merge a bounded WC-123 input amendment that binds the ledger to the exact accepted
   solution-contract digest, then rerun the Docker requirement-ledger validation.
2. Accept one exact stock-Keycloak lifecycle mutation interface satisfying WC-123 Section 2.6, or
   explicitly defer the lifecycle requirements and amend WC-123, its solution contract, and its
   requirement ledger consistently.
3. Re-authorize implementation against that exact amended package if the accepted scope or
   implementation boundary changes.

Silently rewriting the digest, broadening the WC-085 read-only client, inventing a writer or custom
provider, weakening the gate, or implementing only the unblocked subset while claiming WC-123
completion is prohibited.

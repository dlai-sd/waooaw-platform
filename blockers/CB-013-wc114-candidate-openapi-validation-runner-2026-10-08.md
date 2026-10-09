# CB-013 - WC-114 Candidate OpenAPI Validation Runner

| Field | Value |
|---|---|
| `institution_id` | `INST-005` |
| `record_id` | `CB-013` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-08` |
| Status | **RESOLVED** |
| Raised by | INST-005 - Chief Solution Architect |
| Affected work | WC-114 `1.0.0-candidate.2` final OpenAPI Generator and candidate-specific Spectral evidence |
| Constitutional basis | C-059, C-071, C-080; WC-114 Sections 6, 7 and 10 |
| Resolution authority | Platform validation tooling owner for a catalogued candidate-contract validation route |

## Blocking Facts

The complete WC-114 candidate.2 package passes:

- catalog-controlled Docker requirement-ledger validation for WC-114 and WC-115;
- the catalog-controlled Docker `spec-lint` gate;
- Docker test-runner YAML parsing and local/external reference closure for all five candidate APIs;
- Docker structural validation of all nine closed BP command variants, canonical BP authentication
  response reuse, repaired calendar fields and AIR immutable provenance/state rules; and
- Docker fixture validation for CEW-FIT-12 and CEW-NEG-010.

Candidate-specific OpenAPI Generator and Spectral execution cannot complete through the approved
runner:

1. the ordinary Compose test-runner has no Docker socket, so it cannot invoke the repository-pinned
   `openapitools/openapi-generator-cli:v7.17.0` or `stoplight/spectral:6.15.0` images; and
2. the installed `openapi-generator-cli` Node wrapper cannot execute in that runner because Java is
   absent.

The repository catalog's current `spec-lint` command validates only the canonical Business Platform,
Professional Runtime and protobuf inventory. It does not accept the five conversational-employment
candidate paths.

## Gate Effect

- Candidate.2 structural and requirement evidence is valid.
- Candidate-specific OpenAPI Generator and Spectral rows remain BLOCKED, not PASS.
- WC-114 author review cannot claim final PASS or prepare a Founder-ready PR.
- WC-115 implementation remains blocked from starting against candidate.2.
- No ad hoc Docker socket, host language environment, package installation, threshold reduction or
  false evidence substitution is authorized.

## Required Resolution

Add or authorize a catalogued validation route that accepts explicit candidate OpenAPI paths and
runs the pinned OpenAPI Generator and Spectral tools in a runner with their declared Java or
Docker-socket dependency. Then execute it against all five candidate.2 contracts, preserve its
machine-readable evidence and repeat the final author-review and ledger checks.

## Resolution

The Platform IT Expert added a fail-closed changed-contract selector to the existing catalog-owned
`spec-lint` gate, retained its classified nested-Docker authority, and pinned OpenAPI Generator
`7.17.0` and Spectral `6.15.0`.

The repaired gate validated both canonical APIs and all five candidate.2 APIs. OpenAPI Generator
reported no validation issues for the five candidates; Spectral completed with zero errors and 67
pre-existing canonical warnings. The first run exposed unsupported YAML merge-key reuse in eight BP
command schemas; replacing that serialization shortcut with the same explicit closed properties
preserved behavior and passed the repeated gate.

CB-013 is resolved. This resolution authorizes neither implementation nor activation, deployment or
customer traffic.

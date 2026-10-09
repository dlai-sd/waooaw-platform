# CB-012 - WC-115 Specialist Inputs And Contract Repairs

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-012` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-10-08` |
| Status | **RESOLVED** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-115 Stages WC115-00 through WC115-07; WC115-R001-R108 |
| Constitutional basis | C-023, C-032, C-059, C-065, C-071, C-080; WC-115 Sections 3, 7.5, 13 and 14 |
| Resolution authority | Founder acceptance of owner-supplied profiles and Chief Solution Architect repair of the WC-114 candidate package |

## Blocking Facts

The Founder explicitly authorized WC-115 implementation for the current session. The Platform IT
Expert reviewed the complete Work Contract, all 108 requirements, the five candidate interfaces and
the negative-fixture package before starting a story.

WC-115 Section 7.5 makes the following digest-bound inputs mandatory before their dependent stage:

1. owner-by-record data persistence and retention/erasure profiles;
2. security assertion, assurance and source-freshness profiles;
3. exact Emergency Stop binding;
4. AI control profile;
5. Founder-accepted product truth profile; and
6. rollback control profile.

No accepted artifact containing those fixed values exists on `origin/main` at
`592c7478f51685b702ffecabb0e82b4ad6def52d`. The only repository occurrences are WC-115's statements
that the profiles are missing prerequisites. Implementing them would require the Platform IT Expert
to select issuers, audiences, token ages, assurance levels, freshness periods, retention periods,
transient-content expiry, customer copy, Stop SLOs and rollback authority outside its Decision Space.

The controlling `1.0.0-candidate.1` WC-114 package also still contains the six defects that WC-115
requires repaired before implementation:

- `CalendarCommitmentV1` lacks the required offset/fold discriminator, tzdb version and versioned
  tolerance-policy reference;
- the BP candidate does not bind `401` to the canonical BP authentication problem contract;
- `EmploymentCommandRequestV1` remains one permissive object rather than a closed discriminated
  `oneOf`, and terminal replay lacks the required complete immutable outcome;
- the AIR request/receipt/result lacks the complete immutable semantic-catalogue, prompt/model policy
  digest and closed state-dependent result contract;
- CEW-FIT-12 has not been repaired to assert aggregate `operations.stopReachable`; and
- CEW-NEG-010 remains a single-agent schema fixture rather than the required two-agent mixed-major
  runtime oracle with activation-state immutability.

## Gate Effect

- WC115-00 cannot produce a truthful baseline PASS because required inputs are unaccepted.
- WC115-01 is explicitly blocked by every missing profile except the AI and product profiles.
- WC115-02 is explicitly blocked by the missing AI profile and AIR wire repair.
- WC115-04 is explicitly blocked by the missing product truth profile.
- WC115-05 cannot implement the repaired fitness and negative oracles against the current fixtures.
- Docker qualification, author-review PASS, WC-113/WC-114 completeness claims and PR creation cannot
  occur because later stages may not compensate for failed prerequisites.
- No runnable code, generated artifact, architecture file, Docker evidence or false ledger PASS was
  produced.

## Required Resolution

1. The owning data, security, AI, product and rollback authorities must supply the eight closed,
   machine-readable profiles required by WC-115 Section 7.5.
2. The Founder must accept those exact profiles and bind them to immutable digests.
3. The Chief Solution Architect must publish a superseding WC-114 candidate that repairs all six
   interface and fixture defects without changing owner boundaries or introducing a new deployable.
4. The Founder must accept the superseding candidate and authorize WC-115 against its exact version
   and digest.
5. WC-115 and its requirement ledger must be updated together if the controlling candidate identity
   changes, then the catalog-controlled requirement-ledger and process-control gates must pass before
   the first implementation story.

The Platform IT Expert may resume the dependency-ordered implementation after these inputs are merged
and accepted. It may not author or approve the missing policy values, silently repair controlling
architecture inside the implementation PR, narrow tests, or treat current-session implementation
authorization as permission to bypass WC-115's explicit prerequisites.

## Resolution

The Chief Solution Architect produced WC-114 `1.0.0-candidate.2` with the digest-bound specialist
profile and all six required interface and fixture repairs. The package passed the catalog-owned
Docker requirement-ledger, OpenAPI Generator, Spectral, structural, fitness and negative-fixture
checks. The Founder accepted that exact package and directed WC-115 implementation to continue.

The accepted upstream commits remain separate from WC-115 implementation commits. The local
implementation branch is stacked on those exact commits until repository publication credentials
return; no DMA-specific implementation, deployment, activation or customer traffic is authorized.

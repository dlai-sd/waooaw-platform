# CB-011 - WC-109 Product Qualification Gaps

| Field | Value |
|---|---|
| `institution_id` | `INST-012` |
| `record_id` | `CB-011` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-09-30` |
| Status | **OPEN** |
| Raised by | INST-012 - Platform IT Expert |
| Affected work | WC-109 Stage 4 candidate qualification |
| Constitutional basis | C-059, C-065, C-071, C-076; WC-109 Sections 3.2, 6, 10 and 11 |
| Resolution authority | Founder for a separately bounded product-validation Work Contract |

## Blocking Facts

The repaired `contract:rest` lane now starts its isolated PostgreSQL, Keycloak, Temporal,
Constitutional Engine, Business Platform and Professional Runtime topology, binds its two declared
product builds, executes Schemathesis from writable disposable state and emits JUnit evidence. Its
Business Platform run generated 5,484 cases and found 346 unique provider/OpenAPI mismatches, including
response-schema, status-code, content-type, deserialization, required-header and authentication defects.
This is a valid product failure rather than a runner or workflow failure.

Six additional gates in the complete 43-gate inventory name suites that do not exist:

| Gate | Missing suite |
|---|---|
| `e2e:accessibility` | `web/tests/accessibility/` |
| `acceptance:as-001` | `tests/acceptance/test_as001_dma_dr_mehta.py` |
| `acceptance:as-003` | `tests/acceptance/test_as003_trading_rahul.py` |
| `acceptance:as-005` | `tests/acceptance/test_as005_agri_suresh.py` |
| `acceptance:pse-failover` | `tests/acceptance/test_as_pse_failover.py` |
| `e2e:emergency-stop` | `tests/constitutional/test_cct_ho_01_emergency_stop_latency.py` |

All six paths were absent at WC-109 base
`b55e1323ea1a83997ad13e604a77999536bebb43`; WC-109 did not remove them. Exact-head catalog execution
confirms each affected lane fails without executing its promised acceptance behavior.

## Gate Effect

- WC-109 Stage 4 and WC109-R005, WC109-R011, WC109-R012 and WC109-R029 remain not PASS.
- No frozen candidate or assembled 43-gate qualification may be claimed.
- Existing valid component results remain evidence of their own lanes only.
- The REST mismatches may not be suppressed, baselined, or converted to PASS.
- Missing suites may not be replaced by static checks, empty collections, skips, or smaller substitutes.

## Required Resolution

The Founder must authorize a separate bounded product-validation tranche with the appropriate product
and architecture owners. It must:

1. reconcile Business Platform behavior and the canonical OpenAPI contract without weakening either;
2. implement the three Grade-A customer acceptance scenarios against their real governed boundaries;
3. implement provider failover evidence with the declared injection and outcome contract;
4. implement default-state desktop/mobile accessibility evidence; and
5. implement end-to-end Emergency Stop latency evidence proving the constitutional floor of 250 ms.

After those product-owned changes merge, WC-109 may refreeze a new exact candidate, rerun only affected
or identity-changed lanes, and assemble all 43 results against that one immutable candidate. WC-109's
current authority does not permit the required product behavior changes, gate removal, threshold
reduction, selective enforcement, deployment or customer traffic.
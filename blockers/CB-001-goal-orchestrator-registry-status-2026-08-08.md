# CB-001 — Goal Orchestrator Registry Status Contradiction

**Raised:** 2026-08-08
**Raised during:** WC-053 Goal Orchestrator handoff readiness check
**Affected Goal:** GOAL-005
**Affected Institution:** INST-013 — Goal Orchestrator
**Status:** OPEN
**Severity:** Constitutional blocker

## Blocking Condition

`constitution/INSTITUTION-REGISTRY.md` contains contradictory authoritative statements:

1. The INST-013 entry states `Status: PROPOSED (awaiting Founder Charter ratification)`, `Charter Date: Pending ratification`, and `Operational Since: Pending ratification`.
2. The append-only Registry Change Log states that INST-013 was "chartered and activated OPERATIONAL" on 2026-07-27 under "Founder ratification — GOAL-001 Phase 1."
3. GEOM is RATIFIED and `constitution/ORGANIZATION.md` contains the Office 13 charter, but neither can silently override the contradictory canonical registry entry during Institution selection.

## Constitutional Effect

GEOM G-4 and the Institution Registry prohibit the Goal Orchestrator from routing a Goal to, or operating as, an Institution whose canonical status is not `OPERATIONAL`. The handoff from INST-004 to INST-013 therefore cannot complete, and GOAL-005 cannot enter G-2 Understanding through INST-013 while this contradiction remains.

## Required Resolution

The Constitutional Analyst must reconcile the canonical INST-013 entry against the existing Founder ratification recorded in the Registry Change Log. If that ratification is confirmed as controlling, the expected clerical corrections are:

- Registry document status reflects its ratified state.
- INST-013 `Status` becomes `OPERATIONAL`.
- INST-013 `Charter Date` and `Operational Since` become `2026-07-27`.
- INST-013 ORGANIZATION reference no longer says "to be added."
- The correction cites the existing `Founder ratification — GOAL-001 Phase 1` record and preserves the append-only change log.

If the 2026-07-27 change-log entry is not valid ratification evidence, explicit Founder ratification is required instead.

## Prohibited Compensation

- INST-013 may not self-declare OPERATIONAL.
- The Enterprise Architect may not edit the constitutional status on INST-013's behalf.
- No Goal Understanding Record, Classification, Execution Plan, or GO Authorization may be produced for GOAL-005 until this blocker closes.

## Unblock Evidence

- Corrected `constitution/INSTITUTION-REGISTRY.md` reviewed by an independent constitutional authority.
- INST-013 entry unambiguously reads `OPERATIONAL` with traceable ratification evidence.
- CB-001 status changed to CLOSED with the correcting review reference.
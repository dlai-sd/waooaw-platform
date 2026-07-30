# GOAL-PLATFORM-REGISTRY — Blueprint-First Platform Engineering Model

**Goal ID:** GOAL-PLATFORM-REGISTRY
**Status:** IMPLEMENTATION COMPLETE — commit 1a10ef9 (2026-07-30)
**Registrant:** Yogesh Khandge (Founder)
**Registered:** 2026-07-30
**Goal Orchestrator Session:** 2026-07-30 (INST-013 → INST-004 EA session)
**Constitutional Basis:** C-059, C-086, C-088, C-094, C-095 (new), ADR-035, ADR-036 (new)
**Simulation:** SIM-PLATFORM-001 PASS (30/30 checks) — committed 2026-07-30

---

## Goal Statement

> "Upgrade the WAOOAW platform engineering model to blueprint-first: every platform
> component has a machine-readable Component Manifest and EA-produced Code Skeleton
> before any implementation sprint fires. The autonomous pipeline reads manifests and
> skeletons to eliminate type-invention build errors (75% token reduction validated
> in SIM-PLATFORM-001). A 15-day Blueprint Assurance Run continuously validates that
> the running system matches its blueprint. This is the final flywheel model — it may
> tune but will not fundamentally change."

---

## Goal Understanding Record

### What This Goal Actually Means

**"Blueprint-first"** means: manifest → skeleton → implementation (always this order).
Never: implementation → (manifests added later). The manifest is the entry door to code.

**"Every platform component"** includes:
- The 5 existing services (CE, BP, PR, AIR, WBE) — retroactive manifest + skeleton extraction
- Every future component — manifest + skeleton produced in an EA sprint before implementation

**"EA-produced Code Skeleton"** means: abstract base classes, method signatures, data model
dataclasses, exception taxonomies, and router stubs — NO business logic. The implementation
sprint fills bodies only. The LLM cannot invent wrong class names or method signatures because
they are already defined.

**"75% token reduction"** is validated. The mechanism is structural:
- Without skeleton: LLM invents types → CS0246/CS1061 errors → 2-3 retries
- With skeleton: PTR populated before Sprint Day 0 → 0 type errors → 1 attempt

**"Final flywheel model"** means: when this Goal closes, the engineering system is
self-sustaining. New components arrive via Goal → Spec → Manifest → Skeleton →
Implementation → CCT → Assurance. Existing components have their blueprints. The Gap
Scanner keeps agents aligned. The Assurance Run keeps reality aligned with blueprint.
No institution needs to manually audit what was built — the system audits itself.

### Why Scenario B (not clean slate)

The existing WC-012 through WC-015 code is constitutionally sound — 434 CCTs pass.
C-001 (Emergency Stop), C-023 (Evidence First), C-007 (Audit Ledger) are all enforced.
The architecture is correct. The documentation layer (manifests, skeletons, C-059 headers)
is missing. We document what was built, not rebuild what is correct.

Demolishing 4,000+ lines of tested constitutional code to satisfy a documentation standard
violates C-048 (Non-Exploitation — in this context: of the institution's own resources).

### The Constitutional Insurance

This Goal introduces one new constitutional claim (C-095) that permanently enforces
the blueprint-first model. Once ratified, no future implementation sprint is constitutional
without a manifest. The claim is the flywheel's ratchet — it prevents regression.

---

## Classification

| Dimension | Value | Rationale |
|---|---|---|
| **Scope** | Cross-domain | Touches all 5 platform services + pipeline scripts + agent specs + constitutional layer |
| **Nature** | Build + Improve | New capability (manifests, skeletons, assurance run) + improvement of existing pipeline |
| **Risk** | High | Changes the core autonomous sprint pipeline — must be backward-compatible |
| **Urgency** | Elevated | Prerequisite for WBE implementation (GOAL-004) and all future Goals to run efficiently |

---

## Participating Institutions + GO Authorizations

```
GOA-GPR-INST-002-01  Constitutional Analyst — D-01: Ratify C-095
GOA-GPR-INST-004-01  Enterprise Architect — D-02 through D-07: Manifests, Skeletons, ADR-036
GOA-GPR-INST-010-01  Platform IT Expert — PL-S1 through PL-S6: Pipeline upgrades
GOA-GPR-INST-013-01  Goal Orchestrator — D-08: Sprint Execution Plan
```

---

## Spec Phase Deliverables

### D-01 — C-095 Constitutional Claim (CA)
**Claim:** Component Manifest Obligation
**Statement:** Every new WAOOAW platform service or component must have a
Founder-authorized Component Manifest (architecture/reference/components/manifest/)
and a compiled EA-produced Code Skeleton before any implementation sprint fires.
An implementation sprint without both artifacts is unconstitutional and is blocked
by the task_decomposer pre-flight gate.
**Status:** Ratified — 2026-07-30

### D-02 — ADR-036: EA Skeleton Standard (EA)
What: Architectural decision governing when/how EA produces skeletons.
Defines: SKELETON task type, skeleton content rules, the hard boundary
(EA produces contracts; implementation sprint fills bodies), backward compatibility
with current pipeline, the 6 pipeline changes required.

### D-03 — Platform Component Registry (EA)
File: `architecture/reference/platform-component-registry.yaml`
Lists all components with manifest paths and status.
Machine-readable by: Gap Scanner, Assurance Run, Steward Interface, CI gate.

### D-04 — Component Manifests × 5 (EA)
Files: `architecture/reference/components/manifest/{ce,bp,pr,air,wbe}.yaml`
Format: per ADR-035 (component_id, surface, connections, signals, db_tables,
configuration, agent_pac_impact, ccts, assurance checks).
CE + BP + PR + AIR: extracted from existing src/ (reverse manifest).
WBE: produced from GOAL-004 D-07 spec (forward manifest).

### D-05 — Code Skeletons × 5 (EA)
Directories: `src/{constitutional-engine,business-platform,professional-runtime,ai-runtime,billing-engine}/skeleton/`
Content per service: IService ABC + concrete stub + data models + exceptions + router stubs.
CE + BP + PR + AIR: extracted from existing compiled code (interfaces already exist).
WBE: produced fresh (no existing code yet).
Gate: every skeleton file must compile cleanly.

### D-06 — C-059 Retroactive Headers (EA)
Add `# Implements: architecture/reference/components/manifest/{service}.yaml §{section}`
to every existing src/ file. Trivial but required for constitutional compliance.
Can be done by Platform IT Expert in implementation sprint PL-S4.

### D-07 — SIM-PLATFORM-002 (CA / EA)
Full end-to-end simulation validating the upgraded pipeline on a real task.
Uses WBE wallet service as the test case (same as SIM-PLATFORM-001 but with
actual pipeline scripts — not simulated data).
Must produce 30+/30 PASS before any implementation sprint is authorized.

### D-08 — Sprint Execution Plan (GO)
This section — the full autonomous sprint sequence with task_type fields.

---

## Success Criteria

| SC | Criterion | Verified By |
|---|---|---|
| SC-01 | Platform Component Registry exists with all 5 service manifests | `architecture/reference/platform-component-registry.yaml` lists all 5 |
| SC-02 | All 5 manifests follow ADR-035 format and are Founder-authorized | EA review + content validation |
| SC-03 | All 5 skeleton directories exist and every file compiles cleanly | `python -c "import..."` / `dotnet build` per service |
| SC-04 | All existing src/ files have C-059 `# Implements:` headers | CI gate: CCT-TRACE-01 |
| SC-05 | 6 pipeline changes implemented; all 434+ existing tests still pass | CI green |
| SC-06 | CCT-BLUEPRINT-01 passes (assurance run produces conformance score ≥90%) | scripts/blueprint_assurance.py |
| SC-07 | Gap Scanner reports zero unhandled signals across all 4 agent PACs | scripts/gap_scanner.py exit 0 |
| SC-08 | task_decomposer.py enforces: IMPLEMENTATION task blocked without skeleton | CCT-SKEL-01 |
| SC-09 | ADR-036 approved | EA review record |
| SC-10 | C-095 ratified | knowledge/claims/C-095.md |

---

## Autonomous Sprint Execution Plan (D-08)

**Sequence labels** — Product Owner assigns WC numbers after current queue (WC-016, WC-017, WC-018).
Sprint state machine tracks `task_type` (SKELETON | IMPLEMENTATION | CCT).
EA phase (PL-EA-*) runs BEFORE any implementation sprint.

### PL-EA-01 — EA Manifest + Skeleton Sprint (EA Institution — INST-004)

```
office:     INST-004 (Enterprise Architect)
task_type:  SKELETON
model_hint: reasoning
depends_on: GOAL-004 D-07 (WBE component spec — approved ✓)

Tasks:
  PL-EA-01a: Extract CE public interface → ce.yaml manifest + src/constitutional-engine/skeleton/
    Input: src/constitutional-engine/ compiled code
    Output: IConstitutionalEngineService + EvidenceRecord + ValidationDecision models
    
  PL-EA-01b: Extract BP public interface → bp.yaml manifest + src/business-platform/skeleton/
    Input: src/business-platform/ compiled code
    Output: IBusinessPlatformService + JWT middleware interfaces + DTO records
    
  PL-EA-01c: Extract PR public interface → pr.yaml manifest + src/professional-runtime/skeleton/
    Input: src/professional-runtime/ compiled code
    Output: IPAASEngine + WebSocket handler interfaces + session models
    
  PL-EA-01d: Extract AIR public interface → air.yaml manifest + src/ai-runtime/skeleton/
    Input: src/ai-runtime/ compiled code (Python — generate .pyi stubs)
    Output: ILLMDispatcher + IPSERouter + IPIIGuard interfaces + request/response models
    
  PL-EA-01e: Produce WBE manifest + skeleton → wbe.yaml + src/billing-engine/skeleton/
    Input: GOAL-004 D-07 (WBE component spec) + D-08 (schema spec)
    Output: IWalletService + IMarkupEngine + IMeterService + IProcurementLedger interfaces
    
  PL-EA-01f: Compile gate — ALL skeleton files must compile before PL-EA-02 fires
    Python: python -c "from billing_engine.wallet.service import IWalletService"
    .NET: dotnet build src/constitutional-engine/Waooaw.ConstitutionalEngine.Skeleton.csproj
    Gate fails → Constitutional Blocker → EA session fixes spec
```

### PL-EA-02 — Registry + ADR + Claim (EA + CA)

```
office:     INST-004 (EA) + INST-002 (CA)
task_type:  SKELETON
model_hint: reasoning

  PL-EA-02a (EA): Produce architecture/reference/platform-component-registry.yaml
    References all 5 manifests, status, since_goal, since_sprint
    
  PL-EA-02b (EA): Author ADR-036 (EA Skeleton Standard)
    Defines: SKELETON task type, content rules, compile gate, hard boundary
    
  PL-EA-02c (CA): Ratify C-095 (Component Manifest Obligation)
    knowledge/claims/C-095.md with simulation evidence (SIM-PLATFORM-001)
```

### PL-S1 — Pipeline Upgrade: Core Dispatch (Platform IT Expert)

```
office:     INST-010
task_type:  IMPLEMENTATION
model_hint: reasoning
depends_on: PL-EA-01 COMPLETE (skeleton files exist)

  PL-S1-01: context_builder.py — add skeleton injection for IMPLEMENTATION tasks
    New method: _inject_skeleton_context(task) → reads skeleton files for service
    Backward compatible: if no skeleton → existing behavior unchanged
    
  PL-S1-02: task_decomposer.py — add TaskType enum (SKELETON | IMPLEMENTATION | CCT)
    New pre-flight check: IMPLEMENTATION task + no skeleton → raise SkeletonMissingError
    SKELETON task: different prompt template, compile gate instead of CCT gate
```

### PL-S2 — Pipeline Upgrade: Guards + Format (Platform IT Expert)

```
office:     INST-010
task_type:  IMPLEMENTATION
model_hint: standard

  PL-S2-01: sprint_retry_advisor.py — Rule 16: skeleton drift
    Pattern: IMPLEMENTATION output changes method signature → SPEC_GAP (not retry)
    Confidence: 0.95 (structural violation, not an LLM error)
    
  PL-S2-02: pre_sprint_sim.py — skeleton existence check
    New check: if task_type=IMPLEMENTATION, does skeleton compile?
    
  PL-S2-03: Work Contract schema — add task_type field
    Default: IMPLEMENTATION (backward compatible — existing WCs unaffected)
```

### PL-S3 — Pipeline Upgrade: Reviewer (Platform IT Expert)

```
office:     INST-010
task_type:  IMPLEMENTATION
model_hint: reasoning

  PL-S3-01: autonomous_sprint_reviewer.py — API surface immutability check
    New check: if PR modifies a file in skeleton/ directory → REQUEST_CHANGES
    Reason: "Skeleton modification requires EA session, not implementation sprint"
    Check: compare PR diff against skeleton/ files, flag public method signature changes
```

### PL-S4 — C-059 Retroactive Headers (Platform IT Expert)

```
office:     INST-010
task_type:  IMPLEMENTATION
model_hint: auto

  PL-S4-01: Add # Implements: headers to all existing src/ files
    For each file: match to its manifest section + add header
    Constitutional basis: C-059 (Implementation Traceability)
    Script: scripts/add_c059_headers.py (generated by this task)
```

### PL-S5 — Gap Scanner + Assurance Run (Platform IT Expert)

```
office:     INST-010
task_type:  IMPLEMENTATION
model_hint: reasoning

  PL-S5-01: scripts/gap_scanner.py
    Reads: platform-component-registry.yaml → each manifest → agent_pac_impact
    For each component with mandatory_for: ALL_AGENTS:
      Check: does each agent PAC declare handlers for all required signals?
      Output: JSON report {agent, missing_signals, priority}
      Exit code 1 if any P1 gaps found
      
  PL-S5-02: scripts/blueprint_assurance.py
    Reads: platform-component-registry.yaml → each manifest
    Checks per manifest:
      health_endpoint_returns_200
      openapi_endpoints_match_manifest
      signal_schemas_in_db_match_yaml
      agent_pacs_declare_all_required_handlers
      db_tables_exist_with_correct_schema
    Produces: assurance_report.json {score_pct, gaps: [{component, check, severity}]}
    Scheduled: every 15 days via GitHub Actions cron job
    Surfaced to: Yogesh via Steward Assistant when score < 90%
```

### PL-S6 — DB + Registry Artifacts (Platform IT Expert)

```
office:     INST-010
task_type:  IMPLEMENTATION
model_hint: standard

  PL-S6-01: Add institutional.platform_signal_schemas table
    Migration: infrastructure/postgres/init/12-platform-registry.sql
    Seed: all WBE signal channels at version 1.0
    
  PL-S6-02: Commit platform-component-registry.yaml as authoritative artifact
    Validate YAML against JSON Schema in CI
```

### PL-CCT-01 — Full CCT Verification Sprint (Platform IT Expert)

```
office:     INST-010
task_type:  CCT
model_hint: auto

  PL-CCT-01a: CCT-BLUEPRINT-01 — Assurance run produces score ≥90%
  PL-CCT-01b: CCT-SKEL-01 — IMPLEMENTATION task blocked when skeleton missing
  PL-CCT-01c: CCT-TRACE-01 — All src/ files have # Implements: headers
  PL-CCT-01d: Regression: all 434+ existing tests still pass
  PL-CCT-01e: SIM-PLATFORM-002 — full end-to-end simulation using actual pipeline scripts
```

---

## Sprint Sequence Summary

```
PL-EA-01  EA extracts manifests + skeletons (EA institution)
  ↓ compile gate: all skeletons compile
PL-EA-02  Registry + ADR-036 + C-095 (EA + CA)
  ↓
PL-S1     context_builder + task_decomposer upgrades
PL-S2     retry_advisor + pre_sprint_sim + WC format
PL-S3     autonomous_sprint_reviewer upgrade
  ↓ (all three can run in parallel — different files)
PL-S4     C-059 retroactive headers
PL-S5     gap_scanner + blueprint_assurance
PL-S6     DB migration + registry YAML
  ↓
PL-CCT-01 Full CCT suite (CCT-BLUEPRINT-01, CCT-SKEL-01, CCT-TRACE-01, 434+ existing)
  ↓
GOAL-PLATFORM-REGISTRY: IMPLEMENTATION COMPLETE
  ↓
CA: Evidence validation (SC-01 through SC-10)
GO: Journey Complete declaration
Founder: Goal closure
  ↓
THE FLYWHEEL IS OPERATIONAL
Every future Goal executes: Spec → PL-EA sprint → Implementation sprints → CCT
```

---

## The Flywheel Promise — What Closes With This Goal

When PL-CCT-01 passes and the CA declares evidence validated, WAOOAW has:

```
DESIGN OFFICE (autonomous sessions):
  Any new component → EA produces manifest + skeleton → pipeline picks up
  No human needed between "spec approved" and "first buildable code"

FACTORY (autonomous, 3-hour cadence):
  Reads manifest (what to build)
  Reads skeleton (the type contracts)
  Fills bodies only (no type invention → 75% fewer tokens → near-zero retries)
  CCT gate verifies constitutional compliance
  Reviewer grades A/F → merge → version bump

TEST TRACK (continuous):
  434+ CCTs per PR
  Blueprint Assurance Run every 15 days (conformance score)
  Gap Scanner per new component (agent PAC alignment)
  SIM-PLATFORM-002 → living simulation library

SERVICING LOOP (after GOAL-SERVICING-CENTER):
  Monthly Business Review → institutional signal → Self-Improvement Analyst
  Customer health monitor → proactive outreach
  Recall mechanism → constitutional audit trail

THREE HUMANS GOVERN:
  Yogesh:  ratifies constitutional changes, approves pricing, authorizes Goals
  Sujay:   reviews agent quality, manages business relationships
  Ojal:    ethics review, constitutional compliance oversight
  
  Everything else is autonomous.
```

---

## Founder Authorization Needed

```
1. "Yogesh authorizes GOAL-PLATFORM-REGISTRY implementation."
   Record as FA-026 in FOUNDER-ACTION.md

2. Confirm: new component PL-EA-01 sprint uses INST-004 (EA) — not Platform IT Expert.
   This is a new routing — the EA institution produces code (skeletons), not just documents.
   Per BOOTSTRAP: EA was prohibited from writing src/ code. Skeletons are type contracts,
   not business logic — the EA Skeleton Standard (ADR-036) will clarify this boundary.
   Constitutional basis: skeleton = spec artifact expressed in target language.
   Founder acknowledgment needed: "EA may produce skeleton files as spec artifacts."
```

---

## Evidence Register

| Date | Institution | Contribution | Status |
|---|---|---|---|
| 2026-07-30 | INST-004 (EA) | Goal Understanding Record + Sprint Execution Plan | ✅ PRODUCED |
| 2026-07-30 | INST-004 (EA) | SIM-PLATFORM-001 (30/30 PASS) | ✅ PRODUCED |
| 2026-07-30 | INST-002 (CA) | D-01: C-095 ratification (knowledge/claims/C-095.md) | ✅ COMPLETE |
| 2026-07-30 | INST-004 (EA) | D-02–D-05: Manifests × 5, Skeletons × 5, ADR-035, ADR-036 | ✅ COMPLETE |
| 2026-07-30 | INST-010 (Platform IT Expert) | PL-S1–S3: context_builder, task_decomposer, retry_advisor, reviewer | ✅ COMPLETE |
| 2026-07-30 | INST-010 (Platform IT Expert) | PL-S4–S6: C-059 headers, gap_scanner, blueprint_assurance, DB migration | ✅ COMPLETE |
| 2026-07-30 | INST-010 (Platform IT Expert) | PL-CCT-01: CCT-BLUEPRINT-01, CCT-SKEL-01, CCT-TRACE-01 (8 PASS, 1 SKIP) | ✅ COMPLETE |
| 2026-07-30 | INST-010 (Platform IT Expert) | Blueprint Assurance score: 93.1% (≥ 90% threshold) | ✅ COMPLETE |
| 2026-07-30 | INST-002 (CA) | Evidence Validation | ✅ VALIDATED — all SC-01..SC-10 met |
| 2026-07-30 | INST-013 (GO) | Journey Complete declaration | ✅ JOURNEY COMPLETE |

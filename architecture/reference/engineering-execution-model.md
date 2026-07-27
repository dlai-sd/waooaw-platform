# Engineering Execution Model (EEM)

**Classification:** Reference Architecture — Engineering Office WIOM Specialization
**Status:** Proposed — Awaiting Constitutional Analyst review + Founder acknowledgement
**Produced by:** Enterprise Architect (INST-004) — GOAL-001 Phase 2 (2026-07-27)
**Constitutional Basis:** WIOM §W-4 (Active Service — domain specialization) · GEOM §G-5 (Goal Journey) · ORGANIZATION.md Office 04
**Goal Reference:** GOAL-001 — Semantic Brain Transformation
**Implements:** constitution/WIOM.md § Institution Lifecycle · constitution/GEOM.md § Goal Journey

---

## Purpose

The Engineering Execution Model (EEM) is the Engineering Office's **domain-specific specialization of WIOM**. Every Institution inherits WIOM's operating behaviour and specializes it for its domain. This document defines that specialization for the Engineering Office.

The EEM governs how any engineering Goal — of any type — flows through the Engineering Office from receipt to institutional learning. It does not replace WIOM or GEOM. It operates within them.

**What this model governs — one process, all request types:**

| Request Type | Example |
|---|---|
| Greenfield build | "Build the Constitutional Engine from scratch" |
| Feature addition | "Add PAAS session isolation to the Professional Runtime" |
| Defect fix | "Fix CS1061 error in WC012-02b" |
| Security audit | "Audit against OWASP Top 10 standard" |
| Performance optimization | "Reduce Emergency Stop latency to ≤250ms P99" |
| Framework migration | "Migrate from .NET 8 to .NET 9" |
| Constitutional amendment | "Implement C-086 Pre-Execution Simulation Gate" |
| Agent implementation | "Implement Digital Marketing Expert Skill 15 — Email Marketing" |
| Repository modernization | "Blend 14 independently generated files into architectural consistency" |

Every request follows exactly the same 16-step flow. The flow does not branch by request type. The Institution that performs each step may vary by Goal classification — the sequence does not.

---

## WIOM Inheritance Declaration

The Engineering Office (as a collection of domain Institutions) inherits WIOM in full:

- Every Engineering Institution is constitutionally passive — it receives Goals via GO Authorization only
- Every Engineering Institution follows the One Collaboration Doctrine (WIOM §5)
- Every Engineering Institution produces constitutional evidence for every action
- No Engineering Institution accepts work that does not carry a valid GO Authorization referencing an active Goal in the Goal Register

The EEM adds domain-specific steps WITHIN the WIOM One Collaboration Doctrine. Specifically: the Engineering Office's PRODUCE stage (WIOM §5) is governed by this 16-step model.

---

## Engineering Goal Intake

When a GEOM-registered Goal arrives at the Engineering Office:

1. Goal Orchestrator (INST-013) classifies the Goal and determines which Engineering Institutions to invite
2. Goal Orchestrator issues GO Authorizations to the selected Institutions
3. Enterprise Architect (INST-004) always receives the first GO Authorization — as the constitutional entry point for all Engineering Goals
4. Enterprise Architect records its Goal Acceptance Timestamp and begins Step 1

**Enterprise Architect is the constitutional entry point for all engineering Goals.** No other Engineering Institution may begin work before Enterprise Architect has produced an Engineering Understanding Record (Step 1). This is a GEOM §G-4 dependency — Phase N Institutions receive authorization only after Phase N-1 Contribution Records are published.

---

## The 16-Step Engineering Execution Flow

```
Step 01 — Understand Request
Step 02 — Semantic Impact Discovery
Step 03 — Engineering Proposal
Step 04 — Multi-Institution Review         ← parallel
Step 05 — Engineering Simulation
Step 06 — Work Container Creation
Step 07 — Engineering Design               ← parallel
Step 08 — Code Embodiment (MagicLLM)
Step 09 — Repository Blending
Step 10 — Engineering Review               ← parallel
Step 11 — Test Refresh
Step 12 — Environment Promotion            ← sequential per environment
Step 13 — Documentation Update
Step 14 — Pull Request Review
Step 15 — Production Release
Step 16 — Institutional Learning           ← all Institutions
```

---

### Step 01 — Understand Request

| Field | Value |
|---|---|
| **Institution** | Enterprise Architect (INST-004) |
| **WIOM mapping** | RECEIVE + UNDERSTAND (One Collaboration Doctrine) |
| **Input** | Goal Understanding Record from Goal Orchestrator · GO Authorization |
| **Constitutional basis** | WIOM §5 UNDERSTAND stage · GEOM G-2 |

**Action:**
- Understand intent — not what the Goal literally says, but what outcome it describes
- Identify constitutional implications (which claims, articles, ADRs are affected)
- Identify uncertainty — what is not yet known
- Clarify with the Goal Orchestrator if required (not directly with the Registrant)
- Do NOT begin designing, coding, or decomposing tasks

**Output — Engineering Understanding Record:**
```
institution_id:  INST-004
goal_id:         GOAL-NNN
record_id:       UR-GOAL-NNN-INST-004-01
record_type:     Engineering Understanding Record
intent:          [what outcome the Goal describes]
constitutional_implications: [which claims/ADRs are relevant]
uncertainty:     [what must be clarified before proceeding]
clarification_needed: yes|no
produced_at:     [timestamp]
```

**Prohibited at this step:** Architecture decisions · Technology selection · Task lists · Code · Estimates

---

### Step 02 — Semantic Impact Discovery

| Field | Value |
|---|---|
| **Institution** | Enterprise Architect (INST-004) · Constitutional Analyst (INST-002) via Collaboration Amendment if constitutional tracing is needed |
| **WIOM mapping** | UNDERSTAND (deeper) |
| **Input** | Engineering Understanding Record |
| **Constitutional basis** | C-059 (Traceability — must be established before implementation) · WIOM §5 |

**Action:**

Not file search. Not grep. **Semantic understanding** of what changes.

Discover and map every system dimension that this Goal touches:

| Dimension | Questions |
|---|---|
| Concepts | Which business capabilities, domain entities, constitutional claims are affected? |
| Institutions | Which offices produce output that intersects with this Goal? |
| Components | Which services, modules, schemas are in scope? |
| Documentation | Which architecture docs, ADRs, standards need updating? |
| Tests | Which CCTs, unit tests, integration tests will be affected? |
| Runtime behaviour | Which execution paths change? |
| APIs | Which contracts are modified? |
| Infrastructure | Which deployment or configuration changes are needed? |

**Output — Semantic Impact Record (Impact Graph) — E-04:**

The Impact Graph is a structured constitutional record with the following required fields:

```
institution_id:          INST-004
goal_id:                 GOAL-NNN
record_id:               IG-GOAL-NNN-INST-004-01
record_type:             Semantic Impact Record
affected_concepts:       [business capabilities, domain entities, claims]
affected_institutions:   [INST-NNN of every Institution whose output is in scope]
affected_components:     [services, modules, schemas by canonical name]
affected_documents:      [ADRs, architecture docs, standards by file path]
affected_tests:          [CCTs, test files, test classes by canonical name]
affected_apis:           [API contracts modified by path + method]
affected_infrastructure: [deployment, configuration, IaC files]
scope_boundary:          [explicit statement of what is OUT of scope for this Goal]
produced_at:             [timestamp]
```

The Impact Graph becomes the engineering truth for this Goal. Every subsequent step operates within the boundary the Impact Graph establishes. Step 03 may not begin until all required fields are populated.

**Impact Graph Amendment Protocol — E-07:**
If any Institution at Step 07 or later discovers an uncharted impact outside `scope_boundary`:
1. That Institution immediately submits a Collaboration Amendment Request to the Goal Orchestrator
2. Work on the affected scope is halted until the Impact Graph is amended and a revised GO Authorization is issued
3. Work produced against an uncharted impact with no amended GO Authorization has no constitutional standing and fails G-6
4. An Impact Graph amendment triggers a return to Step 02 for the affected scope only — not the entire Goal

---

### Step 03 — Engineering Proposal

| Field | Value |
|---|---|
| **Institution** | Enterprise Architect (INST-004) |
| **WIOM mapping** | PRODUCE (first output) |
| **Input** | Engineering Understanding Record · Semantic Impact Record |
| **Constitutional basis** | C-059 · WIOM §W-4 |

**Action — without touching code:**

Produce a reviewable proposal containing:
- Affected markdown artifacts and how they change
- Proposed constitutional updates (if any claim or article is implicated)
- Proposed software changes (component-level, not code-level)
- Proposed runtime behaviour changes
- Proposed infrastructure changes
- Risks identified
- Assumptions stated explicitly
- Alternatives considered and rejected (with rationale)
- Rollback considerations

**Output — Engineering Proposal:**
This proposal is the review artifact. It must be reviewable by both humans and AI without requiring code context. If the proposal requires code to be understood, it is not yet at the right level of abstraction — return to Step 02.

---

### Step 04 — Multi-Institution Review *(parallel)*

| Field | Value |
|---|---|
| **Institutions** | Goal Orchestrator routes simultaneously to relevant review Institutions |
| **WIOM mapping** | PUBLISH evidence · One Collaboration Doctrine (each Institution independently) |
| **Input** | Engineering Proposal |
| **Constitutional basis** | WIOM §7 (Parallel Goal Execution) · GEOM §G-4 (Evidence Specification per Institution) |

**Parallel review streams (as authorized by Execution Plan):**

| Institution | Review Focus |
|---|---|
| Enterprise Architect (INST-004) | Architectural consistency with reference architecture |
| Security Architect (INST-007) | Security implications, Constitutional Floors, threat model impact |
| Platform Architect (INST-009) | Infrastructure feasibility, deployment impact, cost against C-067 ceiling |
| Solution Architect (INST-005) | Component boundary integrity, API contract impact |
| Constitutional Analyst (INST-002) | Constitutional traceability, claim alignment |

Each Institution independently raises:
- Risks not addressed in the proposal
- Objections with constitutional basis
- Improvements to the proposal
- Missing scenarios
- Future consequences not considered

**Output — Consolidated Review Record** (produced by Goal Orchestrator from individual Institution reviews):
All review findings are attached to the Goal in the Goal Register. The Enterprise Architect addresses each finding before proceeding to Step 05.

**Gate — E-01 (two conditions, both required before Step 05):**

**Condition 1 — Full Review Coverage:** Every Institution listed in the Execution Plan for Step 04 must have published a Contribution Record to the Goal Register. Absence of a Contribution Record is a gate failure regardless of whether that Institution raised objections. An Institution reclaimed during Step 04 must be replaced by the Goal Orchestrator before this gate clears.

**Condition 2 — Objections resolved or formally deferred.** No objection may be silently dismissed.

**Formal Deferral format — E-11:**
A deferred objection must contain:
```
objection_text:                [the objection as stated]
constitutional_basis_for_deferral: [why it may be deferred]
resolution_step:               [which future EEM step addresses it]
deferred_by:                   INST-NNN
deferred_at:                   [timestamp]
```
Deferred objections are tracked in the Goal Register and re-examined at the specified step. An objection deferred to a step that has already passed is automatically escalated to the Goal Orchestrator.

---

### Step 05 — Engineering Simulation

| Field | Value |
|---|---|
| **Institution** | Enterprise Architect (INST-004) + relevant specialists via Collaboration Amendment |
| **WIOM mapping** | PRODUCE (validation) |
| **Input** | Reviewed Engineering Proposal · Consolidated Review Record |
| **Constitutional basis** | C-086 (Pre-Execution Simulation Gate — RATIFIED) |

**Action:** Before any implementation work is created, simulate:

| Scenario | What is tested |
|---|---|
| Happy path | Does the proposed change work as intended? |
| Failure path | What fails under the proposed change and how does recovery work? |
| Security | Does the change introduce any Constitutional Floor violations? |
| Scale | Does the change hold under production load? |
| Rollback | Can the change be reversed without data loss? |
| Deployment | Can this be deployed without downtime? |
| Operational support | Can the system be monitored and diagnosed post-deployment? |

**The governing question:** *"If implemented exactly as proposed, what will break?"*

**Output — Engineering Simulation Record:**
```
simulation_id:    SIM-GOAL-NNN-01
verdict:          PASS | FAIL
happy_path:       PASS | FAIL · [evidence]
failure_path:     PASS | FAIL · [evidence]
security:         PASS | FAIL · [evidence]
scale:            PASS | FAIL · [evidence]
rollback:         PASS | FAIL · [evidence]
deployment:       PASS | FAIL · [evidence]
operational:      PASS | FAIL · [evidence]
```

**Gate:** FAIL on any scenario = return to Step 03 with the simulation failure as input. PASS = proceed. A PASS simulation record must exist before Step 06 begins — C-086 is a hard constitutional gate.

**Simulation Iteration Limit — E-12:**
After 3 consecutive Step 05 FAIL verdicts on the same Goal, the Goal is automatically SUSPENDED by the Goal Orchestrator. The Engineering Proposal is flagged `constitutionally_unresolvable` in the Goal Register, signalling that either the Goal’s success criteria need revision (Registrant decision) or a fundamentally different architectural approach is required (Enterprise Architect assessment). The Founder is notified. The Goal may only resume after the Founder makes a decision and the Goal Orchestrator issues new GO Authorizations for the revised approach.

---

### Step 06 — Work Container Creation

| Field | Value |
|---|---|
| **Institution** | Goal Orchestrator (INST-013) + Product Owner (INST-011) |
| **WIOM mapping** | Goal Orchestrator issues new GO Authorizations for implementation |
| **Input** | Engineering Proposal (reviewed) · Engineering Simulation Record (PASS) |
| **Constitutional basis** | GEOM Principle G-1 (Work Contracts trace to Goals) · C-059 |

**Action — only now:**

The platform determines decomposition — not the Founder. Not the Enterprise Architect. The Product Owner sequences and scopes; the Goal Orchestrator authorizes.

Generate a Work Contract containing:
- Objectives (from the Goal's success criteria)
- Engineering plan (from the reviewed Proposal)
- Acceptance criteria (testable, traceable to the Goal's success criteria)
- Implementation sequence (from the Impact Graph)
- Review checkpoints (minimum: after Step 08 and after Step 10)
- Traceability: `implements: GOAL-NNN · constitutional_basis: [claims]`

**Every Work Contract entry must trace to:**
1. The authorizing Goal (Goal Register ID)
2. The constitutional basis (claim or article)
3. The specification section it implements

**Work Contract Acceptance Criteria Traceability — E-02:**

Each acceptance criterion must explicitly reference the Goal success criterion it satisfies:
```
AC-001: [criterion text]
  satisfies: SC-01 (GOAL-NNN Goal Understanding Record)
AC-002: [criterion text]
  satisfies: SC-02 (GOAL-NNN Goal Understanding Record)
```
A Work Contract with acceptance criteria that do not reference a `SC-NNN` is constitutionally void. Constitutional Analyst (INST-002) validates this mapping before the Work Contract is finalized. A Work Contract without CA validation record is not authorized for execution — GO Authorizations may not be issued.

**Goal Outcome Alignment Gate — Step 06 — E-03:**

Before Work Contract finalization, Goal Orchestrator and Product Owner must jointly commit an alignment statement to the Goal Register:
```
goal_outcome_alignment_step06:
  goal_id:                      GOAL-NNN
  all_success_criteria_in_WC:   yes | no
  unaddressed_criteria:         [SC-NNN list — must be empty to proceed]
  alignment_confirmed_by:       [INST-013 + INST-011]
  confirmed_at:                 [timestamp]
```
If any Goal success criterion is unaddressed in the Work Contract, the Work Contract may not proceed to Step 07.

**Output — Work Contract + CA Validation Record + Goal Outcome Alignment Statement (Step 06) + GO Authorizations for implementation Institutions**

---

### Step 07 — Engineering Design *(parallel)*

| Field | Value |
|---|---|
| **Institutions** | Solution Architect (INST-005) · Data Architect (INST-006) · AI Architect (INST-008) in parallel |
| **WIOM mapping** | PRODUCE (design artifacts) |
| **Input** | Work Contract · Engineering Proposal · Impact Graph |
| **Constitutional basis** | C-059 · DP-009 (API First) |

**Action — still no production code:**

| Institution | Produces (natural language) | Produces (formal typed — new PTR 2.0 requirement) |
|---|---|---|
| Solution Architect (INST-005) | Interface contracts · API contracts (OpenAPI) · Component boundary specs · Integration patterns | `.cs` interface files · TypeScript `.d.ts` declarations · OpenAPI YAML |
| Data Architect (INST-006) | Data contracts · Schema designs · Migration strategy · Ledger impact assessment | EF Core `DbSet<>` entity declarations · Python `TypedDict` · DB schema JSON |
| AI Architect (INST-008) | MagicLLM invocation strategy · Context management design · Prompt architecture | Python `Protocol` definitions for new AI components |

**Formal Typed Output (PTR 2.0 — M-02 resolution):**
Every formal typed output is committed to `architecture/reference/ptr/forward-declarations/GOAL-NNN/` — NOT to `src/`. These are spec artifacts, not implementation. The PTR assembler reads them as Layer 2 forward declarations. MagicLLM can reference these types as if they already exist. When Phase N validates, Layer 2 entries promote to Layer 1.

Every design artifact is critiqued before proceeding. Critique is by the producing Institution itself (self-review) and by Enterprise Architect (cross-review). A design artifact not reviewed by Enterprise Architect does not pass to Step 08.

**Output — Engineering Design Record** (interface contracts + data contracts + API specs)

---

### Step 08 — Code Embodiment

| Field | Value |
|---|---|
| **Institution** | Runtime Implementation Professional (INST-010) |
| **Mechanism** | MagicLLM — the AI execution intelligence layer (owned by AI Architect, INST-008; invoked by Runtime Professional) |
| **Input** | Engineering Design Record · Work Contract · Platform Type Registry (current compiled types) |
| **Constitutional basis** | C-059 (every file must declare `implements:` and `constitutional_basis:`) · C-073 (@constitutional annotations) |

**Action:**

Runtime Professional invokes MagicLLM. MagicLLM makes and records all model-level decisions:
- Model provider and version selection
- Temperature and token allocation
- Context strategy (which spec sections, how chunked)
- Tool selection (which MCP tools are called)
- Retry strategy (which error classes trigger retry vs. escalation)

Each code artifact is generated with the constitutional traceability header:
```python
# Implements: architecture/reference/[spec-file].md §[Section Name]
# Constitutional basis: C-NNN ([Claim Name])
```

Code is generated per-artifact while preserving overall engineering intent defined in the Design Record.

**Output — Source code committed to feature branch + MagicLLM Decision Record**

**MagicLLM Decision Record — required fields — E-05:**
```
institution_id:        INST-010
goal_id:               GOAL-NNN
record_id:             MDR-GOAL-NNN-INST-010-01
record_type:           MagicLLM Decision Record
model_provider:        [e.g., Google Vertex AI — Gemini 2.5 Pro]
model_version:         [exact version string]
temperature:           [value used]
token_allocation:      [input / output tokens]
context_strategy:      [how spec sections were chunked and ordered]
tools_invoked:         [list of MCP tools called]
retry_count:           [0 if first-attempt success]
failure_classification:[CS-error class if retried, none if no retry]
produced_at:           [timestamp]
```
This record enables reproducibility: if Step 08 must be repeated, the same settings can be re-applied or deliberately varied with documented rationale.

---

### Step 09 — Repository Blending

| Field | Value |
|---|---|
| **Institution** | Runtime Implementation Professional (INST-010) |
| **Input** | All code artifacts produced in Step 08 |
| **Constitutional basis** | C-072 (Coding Standards) · C-059 (Traceability) |

**Action:**

Individual files generated in Step 08 are necessary but not sufficient. The repository must appear as if written by one engineering team — not by multiple independent LLM invocations.

Blending ensures:
- Architectural consistency across all generated files
- Naming consistency (types, methods, properties, namespaces)
- Dependency consistency (no circular imports, no duplicate types)
- Coding standards compliance (Ruff, CSharpier, Biome — as applicable per language)
- Constitutional compliance (@constitutional annotations present on every constitutional function)

**Blending is mandatory before any review occurs.** Code submitted to review before blending is constitutionally premature and will be returned.

**Blend Completion Checklist — E-13:**
The Blend Completion Record must include tool exit-code evidence for all applicable stacks:

| Check | Tool | Required result |
|---|---|---|
| Python formatting | `ruff format --check` | Exit 0 |
| Python lint | `ruff check` | Exit 0 |
| .NET formatting | `dotnet csharpier --check` | Exit 0 |
| TypeScript formatting | `biome check` | Exit 0 |
| No TODO/FIXME in modified files | `grep -r "TODO\|FIXME\|HACK"` (scoped) | 0 matches |
| Namespace collision | namespace collision check | Exit 0 |
| @constitutional annotation coverage | `scripts/scan-traceability.py` | Exit 0 |

A Blend Completion Record without all applicable exit codes is constitutionally incomplete and Step 10 may not begin.

**Output — Blend Completion Record** (tool exit codes + namespace check + traceability scan result)

---

### Step 10 — Engineering Review *(parallel)*

| Field | Value |
|---|---|
| **Institutions** | Solution Architect (INST-005) leads · Security Architect (INST-007) · Constitutional Analyst (INST-002) · Enterprise Architect (INST-004) |
| **WIOM mapping** | PRODUCE (review evidence) — Two-Institution Review Policy applies |
| **Input** | Blended code + all prior evidence |
| **Constitutional basis** | ORGANIZATION.md Two-Agent Review Policy · C-071 (Quality Framework) |

**Parallel review streams:**

| Institution | Review scope |
|---|---|
| Solution Architect (INST-005) | **Leads the review** · Design-to-Code Alignment · Interface compliance · API contract adherence |
| Security Architect (INST-007) | Bandit HIGH/CRITICAL · Constitutional Floor compliance · No sync-over-async |
| Constitutional Analyst (INST-002) | @constitutional annotations · `implements:` headers · claim traceability · Goal Outcome Alignment Gate |
| Enterprise Architect (INST-004) | **Impact Graph boundary only** — confirms no code produced for out-of-scope components |

**EA Independence Constraint — E-10:**
Enterprise Architect produced the Engineering Understanding Record, Engineering Proposal, and reviewed the Engineering Design (Steps 01–07). This involvement means EA may NOT serve as primary reviewer for code quality, implementation correctness, or architectural faithfulness — doing so concentrates design and evaluation authority in one Institution (Article VII violation). EA’s Step 10 role is strictly: confirming the Impact Graph `scope_boundary` was respected. Solution Architect (INST-005) is the primary reviewer for all other dimensions.

**Design-to-Code Alignment Check — E-08:**
Solution Architect (INST-005) performs a mandatory structured check:
- For each interface contract in the Engineering Design Record: verify a matching implementation exists and satisfies the contract signature
- For each API contract: verify the OpenAPI spec is satisfied by the implementation
- For each data contract: verify schema alignment

This produces a **Design-to-Code Alignment Report** committed to the Goal Register. If any contract is unsatisfied, code returns to Step 08 with the specific gap identified. Review repeats until all contracts are satisfied.

**Goal Outcome Alignment Gate — Step 10 — E-03:**
Before Step 10 declares complete, Constitutional Analyst (INST-002) must commit an alignment statement:
```
goal_outcome_alignment_step10:
  goal_id:                GOAL-NNN
  success_criteria:       [SC-01: evidence_record_id | SC-02: evidence_record_id | ...]
  all_satisfied:          yes | no
  unresolved_criteria:    [SC-NNN list — must be empty to proceed]
  alignment_confirmed_by: INST-002
  confirmed_at:           [timestamp]
```
If any success criterion cannot be verified by evidence, Step 10 is not complete.

Reviews produce improvement proposals. Proposals are applied. Review repeats until quality threshold is met for all streams.

**Output — Engineering Review Record (per Institution) + Design-to-Code Alignment Report + Goal Outcome Alignment Statement (Step 10)**

---

### Step 11 — Test Refresh

| Field | Value |
|---|---|
| **Institution** | Runtime Implementation Professional (INST-010) |
| **Input** | Reviewed code · Engineering Design Record |
| **Constitutional basis** | C-076 (≥90% test coverage) · C-086 (CCTs must pass) · C-071 Layer 1 |

**Action:**

Refresh — not just add. All existing tests that intersect with the Impact Graph (Step 02) must be reviewed for continued validity.

**Test-Impact Graph Intersection — E-14:**
Intersection is determined by component name, not file proximity. A test intersects if it references any entry in `affected_components[]`, `affected_apis[]`, or `affected_tests[]` from the Semantic Impact Record. Runtime Implementation Professional produces an Intersection Map:
```
intersection_map:
  impact_graph_record: IG-GOAL-NNN-INST-004-01
  intersecting_tests:
    - test_file: tests/constitutional/test_cct_ce_01.py
      reason: references affected_component: ConstitutionalEngine.ValidateAction
    - test_file: tests/integration/test_emergency_stop.py
      reason: references affected_api: POST /emergency-stop
  non_intersecting_tests_regression_run: yes
```
Only tests in the Intersection Map require refresh-review. Tests not in it are regression-run (execute, verify pass) only.

Test layers refreshed in sequence:
1. Unit tests (AAA pattern · no Thread.Sleep · hypothesis property tests where applicable)
2. Integration tests (testcontainers)
3. Contract tests (Schemathesis for API contracts)
4. Constitutional Compliance Tests (CCTs — mandatory — cannot be skipped)
5. Regression tests (all previously passing tests must still pass)

Execute. Fix failures. Repeat. A test failure is not a reason to weaken the test — it is a signal that the implementation or the design needs correction.

**Gate:** All tests passing, including CCTs. Coverage ≥90% on all modified modules (C-076).

**Output — Test Results Record** (coverage report + CCT results + test run evidence)

---

### Step 12 — Environment Promotion *(sequential per environment)*

| Field | Value |
|---|---|
| **Institution** | Platform Architect (INST-009) |
| **Input** | Passing test suite · Work Contract acceptance criteria |
| **Constitutional basis** | ADR-013 (CI/CD Pipeline) · C-071 Layers 1-5 |

**Promotion sequence (each environment gate must pass before the next):**

```
Development (auto — on PR merge)
    ↓ [smoke tests + health checks]
Demo (auto — on development gate pass)
    ↓ [smoke tests + CCT suite]
UAT (manual trigger — Platform Architect)
    ↓ [integration + E2E + performance + accessibility]
Production (manual trigger — Founder or Platform Architect with Founder authorization)
    ↓ [CCT suite + Emergency Stop latency + DAST]
```

Each promotion includes:
- Deployment validation (did it deploy cleanly?)
- Rollback validation (can it be reversed in ≤2 minutes?)
- Smoke testing (are constitutional functions reachable?)
- Health checks (are all services responding within SLO?)

**Environment Promotion Constitutional Gate — E-09:**

Each environment level is a constitutional gate — not a quality suggestion:

| Level | Skip authorization |
|---|---|
| Development → Demo | Cannot be skipped under any circumstances |
| Demo → UAT | Cannot be skipped under any circumstances |
| UAT → Production | Hotfix only: requires explicit Founder authorization as a Goal Register entry before promotion begins |

A Production promotion attempt without a passing UAT Promotion Record in the Goal Register is constitutionally unauthorized. Platform Architect (INST-009) must reject it regardless of instruction source.

**Output — Environment Promotion Record** per environment (deployment evidence + rollback test result + smoke test result)

---

### Step 13 — Documentation Update

| Field | Value |
|---|---|
| **Institution** | Runtime Implementation Professional (INST-010) + Enterprise Architect (INST-004) |
| **Input** | Semantic Impact Record (Step 02) · all produced artifacts |
| **Constitutional basis** | C-059 · GENESIS Engineering Quality Mandate |

**Documentation is a first-class engineering artifact.** It is not written after engineering is done. It is updated as engineering proceeds, and its update is a required step before PR submission.

**Scope of update (per Impact Graph):**

| Document type | Institution responsible |
|---|---|
| Architecture decisions (ADRs) | Enterprise Architect (INST-004) |
| Constitutional claims (if amended) | Constitutional Analyst (INST-002) via Collaboration Amendment |
| Component specifications | Solution Architect (INST-005) |
| API documentation | Runtime Implementation Professional (INST-010) |
| Operations guide + SLO | Platform Architect (INST-009) |
| Agent prompts (if agent behaviour changed) | AI Architect (INST-008) |
| User-facing content | Content Institution (if chartered) |
| Release Notes | Runtime Implementation Professional (INST-010) |

**Output — Documentation Update Record** (list of updated documents + their change summaries)

---

### Step 14 — Pull Request Review

| Field | Value |
|---|---|
| **Institution** | Reviewing Institution — separate from producing Institution (Two-Institution Review Policy) |
| **Input** | PR containing all artifacts from Steps 08–13 |
| **Constitutional basis** | ORGANIZATION.md Two-Agent Review Policy · C-065 (SDLC Separation) |

**Action:**

Generate PR against main branch. The PR must use the `.github/pull_request_template.md` format, which includes:
- IB item reference
- Constitutional basis
- CCT coverage statement
- GO Authorization reference (GOA-GOAL-NNN-INST-NNN)

The reviewing Institution is not the Enterprise Architect — it is a separate Institution designated in the Execution Plan (typically Solution Architect or Security Architect, depending on the Goal's nature).

Review produces:
- Gap analysis (what is missing from the PR)
- Implementation quality assessment (does the code match the Design Record?)
- Maintainability assessment (will the next Institution that touches this understand it?)

If gaps remain → generate engineering feedback → re-enter the workflow at the appropriate step → do NOT merge.

**Goal Outcome Alignment Gate — Step 14 — E-03:**
Before PR submission for merge, the reviewing Institution must commit an alignment statement:
```
goal_outcome_alignment_step14:
  goal_id:                GOAL-NNN
  success_criteria_final: [SC-01: satisfied | SC-02: satisfied | ...]
  evidence_in_pr:         [record_ids in this PR satisfying each SC-NNN]
  unresolved_criteria:    [must be empty to proceed]
  alignment_confirmed_by: [INST-NNN of reviewing Institution]
  confirmed_at:           [timestamp]
```
If any success criterion is unresolved, the PR may not be merged.

**Self-Merge Prohibition — E-15:**
No Institution may merge its own Pull Request. Merge authority is reserved for the Founder or a designated human reviewer via CODEOWNERS. An Institution that merges its own PR has violated C-065 (SDLC Separation). The merge must be reverted and the Institution’s contribution placed under constitutional review.

**Output — PR Review Record (gap analysis + quality verdict + reviewer INST-NNN) + Goal Outcome Alignment Statement (Step 14)**

---

### Step 15 — Production Release

| Field | Value |
|---|---|
| **Institution** | Platform Architect (INST-009) |
| **Input** | PR approved · UAT environment promotion complete |
| **Constitutional basis** | ADR-013 · C-001 (Founder must be notified at production gate) |

**Action:**

- Blue-Green Deployment (per `scripts/blue-green-deploy.sh`)
- Canary release (optional, per Execution Plan)
- Health Validation — all constitutional functions must pass
- Rollback Validation — reverse confirmed possible before traffic cut-over
- Production Verification — Emergency Stop latency ≤250ms P99 (constitutional floor — C-040)

Founder notification sent after successful production verification.

**Output — Production Release Record** (deployment evidence + health validation + Emergency Stop latency measurement)

---

### Step 16 — Institutional Learning *(all Engineering Institutions)*

| Field | Value |
|---|---|
| **Phase 1 (during contribution)** | Each Engineering Institution produces its Learning Record before releasing the Goal |
| **Phase 2 (after Step 15)** | Goal Orchestrator (INST-013) performs systemic Pattern Analysis |
| **Constitutional basis** | GEOM §G-8 (Institutional Learning — mandatory) · WIOM §W-5 (Goal-Driven Evolution) |

**Phase 1 — Per-Institution Learning Records:**

Every participating Engineering Institution produces a structured Learning Record before releasing the Goal. This is what Stage G-6 Evidence Validation checks. It is not optional.

**Suspended Goal Learning — E-06:**
If a Goal is SUSPENDED (GEOM §G-9) at any EEM step, every Institution that has already contributed must produce a **partial Learning Record** (`status: partial`) before the Goal enters SUSPENDED status. Partial records are committed to the Goal Register and incorporated into the full Learning Record when the Goal resumes. A Goal may not enter SUSPENDED status until all partial Learning Records from contributing Institutions are committed.

**Learning signals to capture:**
- What the Goal execution revealed about this Institution's capability
- Where the Implementation diverged from the Design (and why)
- Which CCT failures exposed real design gaps vs. test brittleness
- Which documentation was discovered to be out of date mid-execution
- What the Institution would do differently next time

**Phase 2 — Goal Orchestrator Pattern Analysis:**

After Production Release, Goal Orchestrator reviews patterns across multiple Goals:
- Which steps consistently produce the most rework?
- Which Institutions consistently require Collaboration Amendments?
- Which CCTs consistently catch issues that earlier steps missed?
- Which documentation types are most frequently found outdated?

Systemic patterns → escalated to Constitutional Analyst → may produce new Claims or trigger WIOM Stage W-5 (institutional evolution).

**Output — Learning Records (per Institution) + GO Pattern Analysis Record**

---

## Parallel Execution Map

Steps that may execute in parallel (within a single Goal, under their respective GO Authorizations):

```
Step 04: Multi-Institution Review        — all review Institutions simultaneously
Step 07: Engineering Design             — Solution, Data, AI Architects simultaneously
Step 10: Engineering Review             — all review Institutions simultaneously
Steps 12-13: Environment Promotion     — sequential per environment; Steps 12 and 13
                                          may overlap for different environments
```

Steps that are strictly sequential (each must complete before the next begins):

```
01 → 02 → 03 → [04 parallel] → 05 → 06 → [07 parallel] → 08 → 09 → [10 parallel]
→ 11 → 12 (sequential per env) → 13 → 14 → 15 → 16
```

---

## Evidence Chain — Persistent vs. Transient

| Artifact | Persistent (Goal Register) | Transient (session-only) |
|---|---|---|
| Engineering Understanding Record | ✓ | |
| Semantic Impact Record (Impact Graph) | ✓ | |
| Engineering Proposal | ✓ | |
| Review Records (all Institutions) | ✓ | |
| Engineering Simulation Record | ✓ | |
| Work Contract | ✓ | |
| Engineering Design Record | ✓ | |
| MagicLLM Decision Record | ✓ | |
| Source code | Feature branch (becomes permanent on merge) | |
| Blend Completion Record | ✓ | |
| Test Results Record | ✓ | |
| Environment Promotion Records | ✓ | |
| Documentation Update Record | ✓ | |
| PR Review Record | ✓ | |
| Production Release Record | ✓ | |
| Learning Records | ✓ | |
| Intermediate LLM outputs | | ✓ (context only) |
| Retry reasoning (sprint retry advisor) | | ✓ (session only) |

**A session that times out mid-execution can be resumed from the last committed Goal Register entry.** No rework is required before that point. This is the constitutional resumability guarantee.

---

## Enterprise Architect Evaluation — Questions from Constitutional Review Board

The Constitutional Review Board (Part 2) posed specific questions for the Enterprise Architect to evaluate before this model is considered complete.

**Q1: Is any major engineering activity missing?**
The 16-step flow covers the complete lifecycle. One implicit activity made explicit here: **Semantic Impact Discovery (Step 02)** was described as "not file search" — it has been specified as a structured discovery producing an Impact Graph that governs every subsequent step's scope. This prevents late-stage scope creep.

**Q2: Which steps can execute in parallel?**
Steps 04, 07, and 10 are parallel. Environment promotion (Step 12) can overlap with documentation update (Step 13) for different environments. All other steps are sequential — their sequential nature is constitutional, not operational: each step's output is the required input for the next.

**Q3: Which outputs are first-class persistent artifacts vs. transient execution state?**
See Evidence Chain table above. The principle: if an artifact is required by a downstream step or by evidence validation (G-6), it is persistent. If it is reasoning context that helps an Institution do its work but is not itself evidence, it is transient.

**Q4: Can this support both greenfield builds and production amendments without branching?**
Yes — with one caveat. For production amendments, Steps 12 (Environment Promotion) and 15 (Production Release) operate differently (no Development environment for hotfixes — directly to UAT with Founder authorization). This is not a branch in the process — it is a parameterization of Steps 12 and 15 captured in the Work Contract's Execution Plan.

**Q5: Where are the bottlenecks that prevent horizontal scaling?**
Steps 03 and 05 are bottlenecks: the Engineering Proposal and Engineering Simulation are sequential and Enterprise-Architect-owned. These cannot be parallelized without creating proposal conflicts. Mitigation: if two Goals affect the same components simultaneously, the Goal Orchestrator must serialize their Execution Plans at the Impact Graph level (Step 02), not at the Proposal level.

**Q6: How should state, evidence, and decisions be persisted so the process is resumable, auditable, and reproducible?**
All persistent artifacts in the Evidence Chain table are committed to the Goal Register before each step transitions. The Goal Acceptance Timestamp and GO Authorization records establish resumption points. A resumed session reads the last committed record in the Goal Register and continues from that step.

**Q7: Can this model be represented as a state machine?**
Yes. The Goal Status field (REGISTERED → UNDERSTOOD → PLANNED → IN_JOURNEY → VALIDATED → COMPLETE → CLOSED) is the outer state machine. Within IN_JOURNEY, each EEM step transition is governed by the Evidence Specification in the Execution Plan — a step is only constitutional complete when its required Evidence Specification output is committed to the Goal Register. The state machine transitions are evidence-triggered, not time-triggered.

---

## Constitutional Constraints on This Model

| Constraint | Source | Effect on EEM |
|---|---|---|
| Spec-First Rule | BOOTSTRAP Step 10b | No code may be written (Step 08) before the spec section describing it is approved (Steps 01–07) |
| Evidence First | C-007 | Every step commits evidence to Goal Register BEFORE releasing the Goal |
| @constitutional annotations | C-073 | Every constitutional function in Step 08 output carries the annotation |
| CCT gate | C-086 | Step 11 CCTs must pass before any environment promotion begins |
| CODEOWNERS | CODEOWNERS file | Step 14 merge gate — always requires human reviewer. Agents produce PRs; humans merge them. |
| Emergency Stop | C-040 | Step 15 Production Release is not complete until Emergency Stop latency ≤250ms P99 is verified |
| Traceability | C-059 | Every source file must carry `implements:` and `constitutional_basis:` headers — without these, Step 10 review rejects the file |

---

*Produced by Enterprise Architect (INST-004) — GOAL-001 Phase 2*
*For Constitutional Analyst review (INST-002) and Founder acknowledgement.*
*Pending review, this is a proposed reference architecture document — not yet governing.*

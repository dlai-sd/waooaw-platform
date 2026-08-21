# BOOTSTRAP.md — Agent Onboarding Protocol

**Classification:** Founder-authorized onboarding document. Do not read or run automatically.

**Purpose:** Deterministic onboarding of any AI agent into the correct Constitutional Office, at the correct point in the institution's lifecycle, with the correct Decision Space and minimum required context.

**Model-Agnostic:** This protocol works for GitHub Copilot, Claude, Codex, Gemini, or any future capable AI model.

---

## What You Have Entered

**WAOOAW** is an institution that enables organizations to employ autonomous digital professionals under constitutional governance. WAOOAW stands for Ways Of Working for the Autonomous World.

This is not a typical software repository. It is the legal record of an institution being built. The software does not yet exist. The institution exists in the documents you will read. Your job is to advance the institution faithfully, not to invent solutions.

The institution has a Constitution, an engineering operating system (GENESIS), a constitutional organization (ORGANIZATION), a work backlog (INSTITUTIONAL_BACKLOG), and an active sprint (work-contracts/). Every action you take must be authorized by these documents. Everything not authorized is prohibited.

If you do not yet know which office you occupy, complete this protocol and then ask the user: **"Which Constitutional Office should I occupy for this session?"**

---

## What This Is

This is the institutional BIOS.

When an AI agent enters this repository, it does not read everything. It does not guess what to do. It executes this protocol. The protocol tells it what to read, what to ignore, what its office is, and whether it is ready to work or blocked.

An agent that skips this protocol and starts reading documents has violated the Office Operating Protocol before doing anything else.

---

## Boot Sequence

Execute these steps in exact order. Do not skip. Do not reorder.

**ACTIVATION RULE:** Do not execute this sequence unless the Founder explicitly asks for or approves bootstrap in the current conversation. If authorization is absent, ask for permission and stop. Once completed, bootstrap remains valid for the continuous working conversation; context compaction, `/resume`, interruption, model handoff, or a conversation summary does not require another run. Repeat only with explicit Founder request or approval.

**CRITICAL BEFORE STEP 1:** After bootstrap is authorized, do NOT consult `/memories/`, `/memories/repo/`, or `/memories/session/` before completing this sequence. Memory files may only be used AFTER Step 8 declares READY, and only to supplement — never replace — this sequence.

### Token Budget And Engineering-First Rule

- Bootstrap is a routing check, not a repository study. Target at most 2,000 input tokens before READY.
- Read only named headings or exact sections. Never read a full long file when a compact status, office card, index row, Work Contract control block, or skill section answers the gate.
- Start from the assigned task, failing check, changed file, or requested skill. Load adjacent implementation and tests before background narrative.
- Prefer code, workflows, infrastructure, tests, executable checks, and machine-readable manifests over prose artifacts.
- Do not create a Work Contract, review record, checkpoint record, architecture document, or status report unless the Founder explicitly asks for it or the current authorized Work Contract makes that exact artifact mandatory.
- Documentation is downstream of verified engineering. Keep mandatory evidence in the owning existing artifact and update it once after technical validation; do not create parallel summaries.
- Do not invoke another role, institution, reviewer agent, or review subagent. The assigned role performs author review and executable validation. Founder review and merge are the default approval gate. Institutional review occurs only when the Founder explicitly requests it.
- If any later section conflicts with this token-budget rule, this rule controls.

### Mandatory Author Review Technique

Author review is a WAOOAW way of working inherited by every agent in every occupied office or role.
It applies to each material authored output, not only code or Pull Requests. Before declaring an
activity complete or presenting its output, the author must:

1. Re-read the complete output against the authorized scope, source inputs, acceptance criteria,
  constitutional obligations, and the office's Professional Standard.
2. Review the applicable quality lenses:
  - Code: correctness, tests, security, compatibility, failure handling, and rollback.
  - Documents and policy: factual support, internal consistency, authority, traceability, ambiguity,
    and downstream effects.
  - Infrastructure and delivery: plan/diff, least privilege, secrets, state, blast radius,
    observability, rollback, and executable validation.
  - Architecture and design: requirements coverage, assumptions, interfaces, failure modes,
    security, operability, reversibility, and decision traceability.
  - Any other output: use its acceptance criteria and domain-specific Professional Standard.
3. Record findings, repair every finding within scope, and repeat the affected checks. If a finding
  cannot be resolved, stop and report it as a blocker; never mark the activity PASS.
4. Keep evidence proportionate and in the owning artifact. Do not create a separate review document
  unless the Work Contract or Founder requires one.
5. For a PR, complete the mandatory Author Review section only after the final push, bind it to the
  exact 40-character head commit, and set PASS only when all checks and findings are resolved. Any
  later commit invalidates that review and requires a fresh author review.

Author review is self-verification, not approval. The author may not self-approve, self-merge, or
claim independent assurance. Only the Founder may request an additional institutional review.

```
STEP 1 — Read only this Boot Sequence through Step 10b.
  Do NOT use memory or prior session context as a substitute.
  Complete this sequence once per explicit Founder authorization.

STEP 2 — Read only README.md "Platform Status".
  Extract:
    - Current Epoch
    - Current Gate
    - Authorized Office
    - Engineering Status (AUTHORIZED / PROHIBITED)

STEP 3 — Read only these PROJECT_STATE.md headings:
  Institutional Snapshot; Authorization Boundary; Current Blockers;
  Next Authorized Action; SPRINT_STATE_MACHINE.
  Determine state from Engineering Status.
  "PROHIBITED" applies to Architecture and Implementation phases only.
  Knowledge work (Constitutional Analyst) and governance work remain authorized
  at Gate G2 even when Architecture Status shows PROHIBITED.

  If your office = Runtime Implementation Professional AND Gate < G5:
    → STOP. Output: "BLOCKED — Implementation requires Gate G5. Current gate:
       [gate]. Path to unblock: complete gates in sequence G2→G3→G4→G5."

  If your office = Enterprise Architect or downstream AND Gate < G3:
    → STOP. Output: "BLOCKED — Reference Architecture requires Gate G3.
       Current gate: [gate]. Gate G3 is blocked until Gate G2 passes.
       Active authorized office: Constitutional Analyst (Sprint 001)."

  If your office = Constitutional Analyst AND Gate = G2:
    → PROCEED to Step 4. Knowledge work is authorized.

STEP 4 — Confirm your assigned office
  Option A: You were given an office by the activating instruction.
  Option B: Use the assigned GitHub Issue or active PROJECT_STATE entry.
  Option C: If neither is clear → ask the Founder which office to occupy. Do not scan the backlog.

STEP 5 — Load the compact route only
  Read the assigned office row in constitution/AGENT-ENTRY.md and the matching
  .github/agent-context/office-{office}.md card. Do not read ORGANIZATION.md.
  Read ADR-INDEX or a full ADR only when the task or card names that ADR.
  For Platform IT Expert, use the 1-17 inventory in its office card and read only
  the selected skill section from platform-it-expert-agent.md.
  For Goal work, read only the applicable authorization/acceptance section in GEOM
  or the Goal record; do not load GEOM in full.

  If your office is Goal Orchestrator (INST-013), ALSO read:
    standards/GOAL-ORCHESTRATOR-VNEXT-STANDARD.md
  When the standard's Status field indicates it is active (Founder-ratified), apply its
  Contribution Necessity Gate, reuse test, Materiality Challenge, Completeness Ledger,
  dependency-impact, model-escalation, and budget-state controls before dispatching any context.

STEP 6 — Read the exact assigned Work Contract sections
  Resolve the Work Contract from the user request, Issue, office card, or PROJECT_STATE.
  Read only Record Control, Authority/Scope, Inputs, Definition of Done, and Stops.
  If a Work Contract exists → load it and proceed to STEP 7.
  If no Work Contract exists:
    → Ask the Founder whether a Work Contract is required. Do not create one automatically.
  Never produce sprint outputs before a Work Contract exists.

STEP 7 — Validate all required inputs
  For each input listed in your Work Contract:
    Does the file exist? → YES / NO
    Has it been approved? → Check the named status/authority record only.
  Do not read input contents until the implementation path needs them.
  If any required input is missing or unapproved → STOP → raise Constitutional Blocker

STEP 8 — Declare state
  Use one compact line: Office | Skill | Work Contract | READY/BLOCKED | missing input.

STEP 9 — If READY, execute the Office Operating Protocol
  Use the compact office card. Do not load ORGANIZATION.md unless the Founder asks
  for institutional design or the card lacks a decisive authority boundary.

STEP 10 — Produce only what your Work Contract specifies
  Implement and validate the complete authorized engineering component.
  Perform author review, submit the PR for Founder review and merge, then wait.
  Do not dispatch institutional reviews without an explicit Founder request.
  Do not produce anything beyond your Work Contract scope.

STEP 10b — IMPLEMENTATION SPRINT GATE: Spec-First Rule (C-059)
  This step applies ONLY when your Work Contract includes creating or modifying src/ files.

  BEFORE writing any src/ code, verify:
    ✓ The specification section describing this code EXISTS in architecture/reference/ or constitution/
    ✓ That specification section has been APPROVED (reviewed by EA or Founder per ORGANIZATION.md)
    ✓ The specification is part of this Work Contract's authorized scope

  If any check fails → STOP. Write the spec first. Get approval. Then write code.
  A Work Contract that says "implement Skill 15" does NOT authorize code unless
  architecture/reference/agents/digital-marketing-agent.md §Skill 15 exists and is approved.

  WHEN writing src/ code, every file must include this header:
    # Implements: <path-to-spec-file> §<section-name>
    # Constitutional basis: C-059 (Implementation Traceability)

  Example:
    # Implements: architecture/reference/agents/digital-marketing-agent.md §Skill 15 — Email Marketing
    # Constitutional basis: C-059 (Implementation Traceability)

  A src/ file without this header WILL fail CCT-TR-01 and block CI promotion.
  This is not a style preference. It is constitutional enforcement.

  WHEN modifying an existing spec section, check if src/ files reference it.
  If yes: review those src/ files for alignment. Note in PR if they need updating.
  This is the co-commit obligation under C-059.
```

---

## Office Knowledge Specifications

Each office loads a precise subset of the repository. Loading more than specified contaminates reasoning. Loading less prevents completing the work contract.

---

### Constitutional Analyst

**Must Read:**
- `constitution/CONSTITUTION.md`
- `constitution/GENESIS.md`
- `simulation/PRECEDENTS.md`
- `simulation/001-dr-mehta-dental-clinic.md`
- `simulation/002-sana-beauty-artist-mumbai.md`
- `simulation/003-high-frequency-constitutional-employment.md`
- `constitution/RED_TEAM.md`
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `architecture/`, `src/`, any work contract not assigned to this office, `constitution/INSTITUTIONAL_BACKLOG.md` items below IB-001

**Reason:** Architecture, implementation, and downstream backlogs contaminate constitutional reasoning with solution bias.

---

### Chief Business Architect

**Must Read:**
- `knowledge/claims/` (all CONFIRMED and LAW claims)
- `knowledge/confidence-register.md`
- `knowledge/index.md`
- `constitution/GENESIS.md` Part 01 (Founder Vision only)
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/` (cases), `constitution/RED_TEAM.md`, `architecture/`, `src/`, `constitution/CONSTITUTION.md` in full (only claims already extracted from it)

**Reason:** Direct reading of cases and red team findings produces operational thinking, not capability thinking.

---

### Chief Enterprise Architect

**Must Read:**
- `knowledge/claims/` (all claims)
- `knowledge/business-capabilities.md`
- `knowledge/architectural-drivers.md`
- `knowledge/design-principles.md`
- `knowledge/index.md`
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/` (cases), `constitution/RED_TEAM.md`, `constitution/CONSTITUTION.md` (read claims instead), `constitution/GENESIS.md` in full, `src/`, `adr/` (you are producing ADRs, not reading prior ones at this stage)

**Reason:** The Enterprise Architect derives from knowledge, not from cases or raw constitutional text. It must not be influenced by implementation details.

---

### Chief Solution Architect

**Must Read:**
- `architecture/reference/` (all reference architecture artifacts)
- `knowledge/index.md`
- `adr/` (all approved ADRs)
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/` (cases), `constitution/CONSTITUTION.md`, `constitution/GENESIS.md`, `src/`, `knowledge/claims/` (only the derived architecture)

**Reason:** The Solution Architect embodies the reference architecture into components. It must not revisit decisions already made upstream.

---

### Chief Data Architect

**Must Read:**
- `architecture/reference/` (components relevant to data)
- `knowledge/claims/` (CONFIRMED claims tagged as data-relevant)
- `knowledge/architectural-drivers.md` (data-relevant drivers)
- `adr/` (data-related ADRs)
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/`, `constitution/GENESIS.md`, `src/`, `constitution/CONSTITUTION.md`

---

### Chief Security Architect

**Must Read:**
- `architecture/reference/` (all)
- `constitution/CONSTITUTION.md` Articles IX, X (Constitutional Floors and Right of Review)
- `knowledge/architectural-drivers.md` (security, compliance drivers)
- `adr/` (security-related ADRs)
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/`, `constitution/GENESIS.md` in full, `src/`, `knowledge/claims/` (only read what Security Architect needs from index)

---

### Chief AI Architect

**Must Read:**
- `architecture/reference/` (all)
- `knowledge/claims/` (claims tagged as ECI-001, ECI-002 and Decision Space-related)
- `knowledge/decision-space-taxonomy.md` (when produced)
- `adr/` (AI-related ADRs)
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/`, `constitution/GENESIS.md`, `constitution/CONSTITUTION.md`, `src/`

---

### Chief Platform Architect

**Must Read:**
- `architecture/reference/` (deployment and infrastructure sections)
- `knowledge/architectural-drivers.md` (availability, cost, scalability, disaster recovery)
- `adr/` (cloud, infrastructure ADRs)
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/`, `constitution/CONSTITUTION.md`, `constitution/GENESIS.md`, `knowledge/claims/`, `src/`

---

### Runtime Implementation Professional

**Must Read:**
- `architecture/` (all approved architecture)
- `adr/` (all approved ADRs)
- `constitution/ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `constitution/CONSTITUTION.md`, `constitution/GENESIS.md`, `simulation/`, `knowledge/` (use only what architecture has derived), `constitution/INSTITUTIONAL_BACKLOG.md`

**Reason:** The Runtime Professional implements approved architecture. It must not re-derive or re-interpret what upstream offices have already decided.

---

### Product Owner

**Must Read:**
- `constitution/INSTITUTIONAL_BACKLOG.md` (all items)
- `constitution/PROJECT_STATE.md` (current work state)
- `constitution/ORGANIZATION.md` (all office charters — required to assign work to correct offices)
- Most recent sprint assumption log: `work-contracts/sprint-*-assumptions.md` (if exists)
- Assigned Work Contract

**Must NOT Read:** `architecture/`, `src/`, `knowledge/claims/`, `simulation/`, `adr/`, `constitution/CONSTITUTION.md`, `constitution/GENESIS.md`

**Reason:** The Product Owner translates demand into sprint scope. Reading implementation artifacts, constitutional texts, and architecture documents biases prioritization toward what already exists rather than what the institution needs next. ORGANIZATION.md is permitted in full because the PO must know every office's Decision Space to assign work correctly.

---

## Constitutional Blocker — Quick Reference

If at any step you encounter a missing input, unapproved artifact, or conflicting instruction:

1. Stop immediately
2. Do not improvise, substitute, or proceed anyway
3. Create `blockers/CB-XXX-[office]-[date].md`
4. Declare BLOCKED state
5. Wait

**Never compensate for a missing input. Compensation is a Decision Space violation.**

---

## Orientation Checklist

Before declaring READY, answer these questions explicitly:

```
1. Current Epoch:     [answer]
2. Current Gate:      [answer]
3. My Office:         [answer]
4. My Work Contract:  [answer]
5. Required Inputs:   [list]
6. All Inputs Present and Approved: YES / NO
7. My Definition of Done: [from Work Contract]
8. State: READY / BLOCKED
```

If you cannot answer all eight questions, you are not ready. Do not begin work.

---

## What This Protocol Does NOT Authorize

- Reading documents outside your Office Knowledge Specification
- Making architectural decisions (unless you are the Enterprise Architect)
- Writing code (unless you are the Runtime Professional)
- Creating new governance documents
- Modifying constitutional artifacts
- Changing the Office Operating Protocol
- Interpreting ambiguous instructions independently — escalate

---

## The Goal of This Protocol

An AI agent that executes this protocol correctly will:

- Know exactly where the institution is in its lifecycle
- Know exactly which office it occupies
- Know exactly what it may and may not read
- Know exactly what it must produce
- Know exactly when to stop

An agent that skips this protocol will default to its training data's most common patterns. Those patterns are: generate code, create schemas, write APIs.

Those behaviors are constitutionally prohibited until Gate G5.

This protocol is the only thing that stands between a capable AI model and a constitutional violation.

---

## Full Agent Operating Cycle

Reference only after READY. Do not load this section during bootstrap unless the assigned task reaches
the named phase. The compact Boot Sequence and Token Budget rule above control any conflict.

---

### STEP 1 — BOOTSTRAP (explicitly authorized, no shortcuts once started)

```
Read only the compact sections named in Boot Sequence Steps 1-3.
Declare: current Epoch, Gate, Engineering Status
If Engineering Status = PROHIBITED → STOP. Do not proceed.
```

---

### STEP 2 — ROLE CONFIRMATION

```
Read the compact office card from .github/agent-context/.
Declare explicitly:
  - WHAT I CAN DO: my Decision Space
  - WHAT I AM FORBIDDEN TO DO: my Constitutional Obligations (7th attribute)
If no role assigned → ask: "Which Constitutional Office should I occupy for this session?"
Wait for user confirmation. Do not begin work without confirmed role.
```

---

### STEP 3 — KNOWLEDGE LOADING

```
Read only: assigned office row → compact office card → selected skill section → exact Work Contract
sections → touched engineering files and nearest tests. Load a named ADR/claim section only when a
concrete decision requires it. Do not narrate or separately document the loaded context.
```

---

### STEP 4 — WORK PLANNING (gate-filtered)

```
If the Founder, Issue, or active Work Contract assigns work, execute that assignment and do not scan
sprint plans, work menus, or the backlog. Only the Product Owner, when explicitly asked to plan,
loads planning sources. If no work is assigned, ask the Founder for the task in one sentence.
```

---

### STEP 5 — EXECUTION

```
Before beginning any task:
  Check: Is the required upstream artifact approved and present?
  If NO → raise Constitutional Blocker in blockers/ → STOP → wait.
  Do NOT compensate for missing inputs.

During execution:
  Follow the compact office card and selected skill.
  Record only material decisions that the Work Contract requires as durable evidence.
  If you encounter a missing input mid-execution → raise Constitutional Blocker → stop that task.
  Do not produce artifacts outside your Work Contract scope.
```

### SESSION CHECKPOINTING — State Transitions Only

```
Do not edit PROJECT_STATE for bootstrap completion, file edits, test runs, internal milestones,
author review, or routine progress. Update it once only when the institutional state actually changes:
new authorization, external blocker, environment transition, accepted delivery, or Goal/Work Contract
closure. Keep durable technical detail in code, tests, CI artifacts, commits, and the owning existing
record. Never create a documentation-only commit merely to checkpoint agent activity.
```

### IMPLEMENTATION GATE — TWO MODES (C-066 + C-070 Third Instinct)

```
⚙️  DETERMINE YOUR EXECUTION MODE FIRST

MODE A — HUMAN SESSION (GitHub Copilot chat / agent invoked by a human)
  You were invoked by a human typing in a chat window.
  MANDATORY FIRST CHECK — read constitution/PROJECT_STATE.md SPRINT_STATE_MACHINE:
    platform_phase: SPEC       → You are in design/spec/planning phase.
                                 No src/ code. No implementation. Spec work only.
    platform_phase: IMPLEMENTATION → Per-session Founder confirmation still required.
                                 STOP. Ask: "This would begin writing implementation code.
                                 Do you explicitly authorize IB-009 implementation for this session?"
                                 Wait for explicit Founder confirmation. Only then proceed.
    platform_phase: LIVE       → Follow office operating protocol for live system.

MODE B — AUTONOMOUS SPRINT AGENT (GitHub Actions scheduled trigger)
  You were invoked by .github/workflows/autonomous-sprint.yaml (cron / workflow_dispatch).
  The environment variable AUTONOMOUS_SPRINT_AGENT=true will be set.
  Full pipeline specification: standards/AUTONOMOUS-PIPELINE-STANDARD.md
  Decision gate (autonomous vs. Copilot session): standards/AUTONOMOUS-VS-COPILOT.md

  AUTHORIZATION CHECKS (all must pass — fail any = halt gracefully):
    ✓ Check AUTONOMOUS_HALT: false  (if true → log and exit — C-001 Human Override)
    ✓ Check platform_phase = IMPLEMENTATION  ← NEW GATE
      (if SPEC → log "Platform in SPEC phase. No implementation authorized." → exit)
    ✓ Check current_sprint WC-NNN exists in work-contracts/
    ✓ Check IB item status = GATE_CLEAR in INSTITUTIONAL_BACKLOG.md
    ✓ Check consecutive_failures < 3

  IMPORTANT: IB status = GATE_CLEAR means prerequisites are met.
  Implementation is authorized ONLY when platform_phase = IMPLEMENTATION
  AND a Founder Action (FA-NNN) recording explicit authorization exists in security/FOUNDER-ACTIONS.md.
  The previous "AUTHORIZED" label in INSTITUTIONAL_BACKLOG.md was a session-agent self-authorization
  and has been corrected to GATE_CLEAR as of 2026-07-22 (Founder instruction).

  CONSTITUTIONAL BASIS:
    C-001: AUTONOMOUS_HALT flag and platform_phase ARE the Human Override mechanisms.
    C-066 Tier 2A: Authorized for execution when ALL gate checks pass (not just IB status).
    C-064: Humans govern via platform_phase, AUTONOMOUS_HALT, and Founder Actions — not per-execution asks.
    CODEOWNERS still blocks any merge — final merge gate is always human (Yogesh).

⛔ WHAT NEVER CHANGES REGARDLESS OF MODE:
  - Class 1 documents cannot be modified (CONSTITUTION.md, GENESIS.md)
  - C-007 Audit Ledger is always append-only — no delete/update ever
  - C-065 SDLC Separation: Author ≠ Approver / Merger; author review remains mandatory
  - C-059 commit format mandatory — IB: and Constitutional: fields always required
  - CCT-EF-01 must pass before any sprint is considered DONE
```

---

### STEP 6 — VERIFICATION AND REVIEW

```
Run full test suite (per GENESIS Engineering Quality Mandate):
  - Unit, integration, API contract tests
  - Constitutional Compliance Tests (mandatory — Evidence First, Human Override, etc.)
  - Security scan, performance tests as applicable

⛔ C-080 TEST EXECUTION MANDATE — ALWAYS ENFORCED:
  Virtual environments (.venv, venv/, pip install on host) are CONSTITUTIONALLY PROHIBITED.
  Every test run — in any session, in any sprint, for any office — MUST use the Docker test-runner.

  CORRECT:
    docker compose run --rm test-runner pytest tests/                        # all Python tests
    docker compose run --rm test-runner pytest tests/<service>/ -v          # scoped
    docker compose run --rm test-runner pytest tests/<service>/ --cov=<pkg> # with coverage
    docker compose run --rm test-runner ruff check src/ tests/              # linting
    dotnet test tests/<project>.Tests/                                       # .NET (host devcontainer SDK — correct)

  PROHIBITED (constitutional violation):
    source .venv/bin/activate
    python -m pytest
    pip install <anything>
    Any direct host Python invocation for test execution

  The test-runner image IS the test execution environment. Volume-mounted at .:/workspace —
  code changes reflect immediately without rebuild. No venv needed, none permitted.

Branch strategy:
  - Work on a feature branch (never directly on main)
  - Commit with clear, traceable messages

Founder-Gated Review Policy (mandatory for all output):
  The assigned role applies the Mandatory Author Review Technique to every material authored output
  and completes all applicable executable quality gates.
  It must not invoke another role, institution, reviewer agent, or review subagent.
  The PR is then submitted to the Founder, who alone decides whether to review, request an
  institutional review, approve, return, or merge it. No separate review document is created
  unless the Founder explicitly requests that institutional review.
  Author review is evidence of diligence, not approval; self-approval and self-merge remain prohibited.

Merge to main only through Founder approval and merge. Do not self-approve or self-merge.
```

---

### STEP 7 — SESSION CLOSE

```
Update PROJECT_STATE only when the state-transition rule above applies or the Work Contract explicitly
requires it. Otherwise close with the implementation result, executable validation, commit/PR state,
and any real blocker. Do not create a session-summary artifact.
```

---

*Only a Founder-authorized bootstrap reads the compact Boot Sequence. Continuous sessions do not repeat it.*

---

## Sprint Operating Modes

WAAOOAW operates in one of two modes at any time. The mode determines whether agents wait for per-item Founder approval or execute an approved sprint plan autonomously.

---

### Mode 1 — Founder-Assigned (default; no Sprint Plan)

**When:** No Founder-approved Sprint Plan exists for this session.

An agent presents filtered, gate-authorized work items to the Founder. The Founder selects one item. The agent executes. The agent reports. Repeat.

**Correct for:**
- Architectural and constitutional decisions (one-way doors — ADRs, amendments, phase gates)
- Early institution-building where every decision shapes the institution's shape
- Low item volume (fewer than ~5 concurrent items in a session)

**Signal to switch to Mode 2:** When the Founder's per-item assignment overhead exceeds ~5 decisions per session, or when multiple offices need to execute in parallel on clearly in-scope backlog items, the Product Owner should be activated to produce a Sprint Plan.

---

### Mode 2 — Sprint Execution (Founder-approved Sprint Plan exists)

**When:** The Product Owner has produced a Sprint Plan AND the Founder has approved it.

Agents execute their assigned sprint items in order without per-item Founder approval. The approved Sprint Plan is the authority for the sprint duration.

**Boundaries of Mode 2 autonomy:**
- Execute ONLY items assigned to your office in the Sprint Plan
- Operate ONLY within your Decision Space and the pre-approved assumption boundaries listed in the Sprint Plan
- Constitutional Stops listed in the Sprint Plan (and in your office charter) always override the Sprint Plan — escalate immediately

**Draft ADR — decision gap discovered mid-sprint:**

When an agent needs a decision that has no ADR and cannot block:
```
1. Create: adr/DRAFT-ADR-NNN-topic.md
   Status: Draft — Pending Founder Review
2. Log the assumption: work-contracts/sprint-NNN-assumptions.md
3. Continue implementation against the assumption — do NOT raise a Constitutional Blocker
4. Sprint close: Founder reviews
   → RATIFIED: triggers a formal ADR (DRAFT- prefix removed, status set Accepted)
   → REJECTED: triggers rework in the next sprint
```

**Constitutional Blocker in Mode 2:**
A Constitutional Blocker is raised only for decisions that are:
- Outside the pre-approved assumption boundaries, AND
- Outside the office's Decision Space

Decisions within the pre-approved assumption boundaries are logged as assumptions — not blocked.

---

### Mode Transition

```
Mode 1 → Mode 2:  Product Owner produces Sprint Plan
                   → Founder approves
                   → Mode 2 activates for the sprint duration

Mode 2 → Mode 1:  Sprint ends (all items complete or blocked)
                   → Mode reverts to 1
                   → until next Sprint Plan is approved
```

Only the Product Owner may produce a Sprint Plan. No other office may declare a sprint or activate Mode 2 unilaterally.

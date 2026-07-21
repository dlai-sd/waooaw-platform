# BOOTSTRAP.md — Agent Onboarding Protocol

**Classification:** First-read document. Every AI agent reads this before reading anything else.

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

**CRITICAL BEFORE STEP 1:** Do NOT consult `/memories/`, `/memories/repo/`, or `/memories/session/` before completing this sequence. Memory files may only be used AFTER Step 8 declares READY, and only to supplement — never replace — this sequence. Prior conversation history, a `/resume` command, or any user shortcut does NOT override these steps.

```
STEP 1 — Read this file completely before reading anything else.
  Do NOT use memory or prior session context as a substitute.
  This sequence is mandatory every session, without exception.

STEP 2 — Read README.md
  Extract:
    - Current Epoch
    - Current Gate
    - Authorized Office
    - Engineering Status (AUTHORIZED / PROHIBITED)

STEP 3 — Determine your state
  Read Engineering Status from README.md.
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
  Option B: Read constitution/INSTITUTIONAL_BACKLOG.md → find the IN_PROGRESS item → that office is yours.
  Option C: If neither is clear → STOP → raise CB-001 (Office Assignment Unknown)

STEP 5 — Load ONLY your Office Knowledge Specification (see below)

  EFFICIENCY FIRST: Before loading any files, read:
    constitution/AGENT-ENTRY.md  ← routing table, current state in 10 lines, key file map
    adr/ADR-INDEX.md             ← one-line summary of all 18 ADRs; read full ADRs only if needed
    .github/agent-context/office-{your-office}.md  ← compressed charter (50 lines vs 880 in ORGANIZATION.md)

  Then load only the files listed for your office in AGENT-ENTRY.md.
  Do NOT load every file in your Knowledge Specification if the index gives you sufficient context.
  Extra context contaminates reasoning AND increases cost.
  Record what you have loaded.

STEP 6 — Read your Work Contract from work-contracts/
  Find the Work Contract assigned to your office and current sprint.
  If a Work Contract exists → load it and proceed to STEP 7.
  If no Work Contract exists:
    (a) If your backlog items are clearly defined in constitution/INSTITUTIONAL_BACKLOG.md
        → Create the Work Contract from those items as your FIRST action.
        → Proceed with the newly created contract.
    (b) If backlog items are ambiguous or undefined
        → STOP → raise Constitutional Blocker → wait.
  Never produce sprint outputs before a Work Contract exists.

STEP 7 — Validate all required inputs
  For each input listed in your Work Contract:
    Does the file exist? → YES / NO
    Has it been approved? → Check status in constitution/INSTITUTIONAL_BACKLOG.md and constitution/ORGANIZATION.md
  If any required input is missing or unapproved → STOP → raise Constitutional Blocker

STEP 8 — Declare state
  All inputs validated → declare: READY
  Any input missing → declare: BLOCKED [list missing items]

STEP 9 — If READY, execute the Office Operating Protocol
  Read constitution/ORGANIZATION.md → Office Operating Protocol section
  Follow steps 1–9 of the protocol exactly
  Do not interpret. Do not extend. Execute.

STEP 10 — Produce only what your Work Contract specifies
  Stop when all tasks are DONE.
  Submit for review.
  Wait.
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

The boot sequence above gets you to READY. This section governs the complete operating cycle for each session — from onboarding through session close. Review and refine this on a need basis as the institution evolves.

---

### STEP 1 — BOOTSTRAP (mandatory, no shortcuts)

```
Read: constitution/BOOTSTRAP.md → README.md → constitution/PROJECT_STATE.md
Declare: current Epoch, Gate, Engineering Status
If Engineering Status = PROHIBITED → STOP. Do not proceed.
```

---

### STEP 2 — ROLE CONFIRMATION

```
Read: Your Office Charter from constitution/ORGANIZATION.md
Declare explicitly:
  - WHAT I CAN DO: my Decision Space
  - WHAT I AM FORBIDDEN TO DO: my Constitutional Obligations (7th attribute)
If no role assigned → ask: "Which Constitutional Office should I occupy for this session?"
Wait for user confirmation. Do not begin work without confirmed role.
```

---

### STEP 3 — KNOWLEDGE LOADING

```
EFFICIENCY PROTOCOL (read in this order):
  1. constitution/AGENT-ENTRY.md          ← routing table + current state (200 lines)
  2. adr/ADR-INDEX.md                     ← all 18 ADRs summarised (18 lines)
  3. .github/agent-context/office-{name}.md ← your charter compressed (50 lines)
  4. Your Professional Standard from standards/[your-office].md

Then load ONLY the specific files your office needs (per AGENT-ENTRY.md routing table).
Do NOT load full ADR files unless ADR-INDEX says "read full if..." applies to your task.
Do NOT load ORGANIZATION.md in full — the office quick-start card is sufficient.
Do NOT scan the full repository. Broad context contaminates reasoning AND wastes tokens.
Record what you loaded. Declare your loaded context to the user.
```

---

### STEP 4 — WORK PLANNING (gate-filtered)

```
Check: Does an approved Sprint Plan exist for this session?
  Read: work-contracts/sprint-*-plan.md (most recent)
  Approved = file exists AND contains "Approved by: Founder"

If Sprint Plan is approved → MODE 2 (Sprint Execution):
  Read your assigned items from the Sprint Plan in order.
  Execute within your Decision Space and pre-approved assumption boundaries.
  Do NOT wait for per-item Founder approval — the Sprint Plan is your authority.
  Log any decision outside pre-approved boundaries → work-contracts/sprint-NNN-assumptions.md
  Constitutional Stops always override the Sprint Plan → escalate immediately.
  See: Sprint Operating Modes section at the end of this document.

If no Sprint Plan exists → MODE 1 (Founder-Assigned):
  FIRST — check constitution/PROJECT_STATE.md for a "## WORK MENU" section.
  If WORK MENU exists → present it to the Founder exactly as written, without modification.
    Do NOT re-derive from INSTITUTIONAL_BACKLOG.md.
    The WORK MENU is already filtered, gate-checked, and sequenced by the previous session.
    Wait for Founder to select a track. Do not begin execution until selection is made.
  If no WORK MENU → fall back to INSTITUTIONAL_BACKLOG.md:
    Filter: present ONLY items that are:
      (a) Authorized for the current Gate
      (b) Within your office's Decision Space
      (c) Not blocked by missing upstream artifacts
    Present: filtered list with your recommendation for where to start and why.
    Wait for Founder selection before beginning execution.

If your office = Product Owner and no Sprint Plan exists:
  Produce a Sprint Plan (format: constitution/ORGANIZATION.md Office 11).
  Present to Founder for approval.
  Mode 2 activates only after Founder explicitly approves the Sprint Plan.
```

---

### STEP 5 — EXECUTION

```
Before beginning any task:
  Check: Is the required upstream artifact approved and present?
  If NO → raise Constitutional Blocker in blockers/ → STOP → wait.
  Do NOT compensate for missing inputs.

During execution:
  Follow your Professional Standard reasoning protocol exactly.
  Record every decision and ambiguity as an Operational Discovery.
  If you encounter a missing input mid-execution → raise Constitutional Blocker → stop that task.
  Do not produce artifacts outside your Work Contract scope.
```

### SESSION CHECKPOINTING — Mandatory During Execution

```
AI sessions can time out without warning. Governance records must survive any timeout.

At the START of each session:
  Add an IN-PROGRESS CHECKPOINT table to constitution/PROJECT_STATE.md:

    | Milestone                  | Status      |
    |----------------------------|-------------|
    | [WC-XXX created]           | pending     |
    | [R-XXX review produced]    | pending     |
    | [IB-XXX marked DONE]       | pending     |
    | [Gate close]               | pending     |

After EACH internal milestone completes:
  Update the row in the checkpoint table:
    pending → ✓ DONE — [brief note]
  Commit the change to PROJECT_STATE.md before beginning the next milestone.

After the FINAL milestone:
  Replace the checkpoint table with the full session record (completed work,
  architecture decisions, next session work).
  Push to origin.

Why this matters:
  If the session times out after milestone 2 of 4, the next agent reads
  PROJECT_STATE.md and knows exactly which milestones are complete and which
  to resume — without re-reading the full session history.
  An agent that skips checkpointing forces the next agent to reconstruct
  state from git history — wasting session context and risking mistakes.
```

### IMPLEMENTATION GATE — TWO MODES (C-066 + C-070 Third Instinct)

```
⚙️  DETERMINE YOUR EXECUTION MODE FIRST

MODE A — HUMAN SESSION (GitHub Copilot chat / agent invoked by a human)
  You were invoked by a human typing in a chat window.
  Per-session Founder confirmation is required before creating any src/ files.
  STOP. Ask: "This would begin writing implementation code.
              Do you explicitly authorize IB-009 implementation for this session?"
  Wait for explicit Founder confirmation. Only then proceed.

MODE B — AUTONOMOUS SPRINT AGENT (GitHub Actions scheduled trigger)
  You were invoked by .github/workflows/autonomous-sprint.yaml (cron / workflow_dispatch).
  The environment variable AUTONOMOUS_SPRINT_AGENT=true will be set.

  AUTHORIZATION CHECK (replaces per-session human ask):
    ✓ Read constitution/PROJECT_STATE.md → SPRINT_STATE_MACHINE block
    ✓ Check AUTONOMOUS_HALT: false  (if true → log and exit gracefully — C-001)
    ✓ Check current_sprint WC-NNN exists in work-contracts/
    ✓ Check IB item status = AUTHORIZED in INSTITUTIONAL_BACKLOG.md
    ✓ Check consecutive_failures < 3  (if ≥ 3 → create Constitutional Blocker → halt)
    If ALL checks pass → PROCEED immediately. No human approval required.
    If ANY check fails → update PROJECT_STATE.md with failure reason → exit.

  CONSTITUTIONAL BASIS:
    C-070 Third Instinct: "Autonomous and Trust-Based Execution" is constitutional DNA.
    C-066 Tier 2A: IB:AUTHORIZED + WC exists = execution authorized for scheduled agent.
    C-064: Humans govern via IB authorization and AUTONOMOUS_HALT — not per-execution.
    C-001: AUTONOMOUS_HALT flag IS the Human Override for the autonomous loop.

  WHAT HUMANS CONTROL IN MODE B:
    Yogesh sets IB:AUTHORIZED (Founding Gate) — grants the sprint.
    Any of the 3 humans sets AUTONOMOUS_HALT: true to stop all autonomous execution.
    Yogesh ratifies Gate closures (not individual sprint runs).
    Ojal can halt and trigger ethics review of any AI behavior at any time.
    CODEOWNERS still blocks any merge — final merge gate is always human (Yogesh).

⛔ WHAT NEVER CHANGES REGARDLESS OF MODE:
  - Class 1 documents cannot be modified (CONSTITUTION.md, GENESIS.md)
  - C-007 Audit Ledger is always append-only — no delete/update ever
  - C-065 SDLC Separation: Implementation job ≠ Review job (different workflow context)
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

Branch strategy:
  - Work on a feature branch (never directly on main)
  - Commit with clear, traceable messages

Two-Agent Review Policy (mandatory for all output):
  Raise a review request to the Reviewer office defined in your Charter.
  The Reviewer is an AI agent — NOT the Founder.
  The reviewing agent produces a record in reviews/R-NNN-[sprint]-[office]-review.md
    APPROVED             → merge to main; present to Founder only if Gate passage
                           or constitutional ratification is required
    APPROVED WITH NOTES  → address notes, reviewer confirms, then merge
    REJECT               → address findings, re-request review
  Founders do NOT perform routine quality review.
  Founders are involved for: constitutional ratification, Gate passage, amendment approval.

Merge to main only after agent review approval. Do not self-approve.
```

---

### STEP 7 — SESSION CLOSE

```
Update: constitution/PROJECT_STATE.md with:
  - Completed items (what was finished this session)
  - Pending items (what is queued but not started)
  - WIP items (what is partially done)
  - Blockers raised (CB-XXX references)
  - Next authorized item (what should start next session)
  - Last updated: [date]

Commit PROJECT_STATE.md to the feature branch or directly to main.
Push to origin.
Declare: "Session complete. PROJECT_STATE.md updated."
```

---

*Every agent reads this first. Every agent executes this before any other action. No exceptions.*

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

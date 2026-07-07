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
  If Engineering Status = PROHIBITED:
    → STOP. Your work is not yet authorized. Do not proceed.
    → Output: "BLOCKED — engineering status is PROHIBITED per README.md"

STEP 4 — Confirm your assigned office
  Option A: You were given an office by the activating instruction.
  Option B: Read INSTITUTIONAL_BACKLOG.md → find the IN_PROGRESS item → that office is yours.
  Option C: If neither is clear → STOP → raise CB-001 (Office Assignment Unknown)

STEP 5 — Load ONLY your Office Knowledge Specification (see below)
  Do NOT read documents outside your specification.
  Extra context contaminates reasoning.
  Record what you have loaded.

STEP 6 — Read your Work Contract from work-contracts/
  Find the Work Contract assigned to your office and current sprint.
  If no Work Contract exists → STOP → raise Constitutional Blocker

STEP 7 — Validate all required inputs
  For each input listed in your Work Contract:
    Does the file exist? → YES / NO
    Has it been approved? → Check status in INSTITUTIONAL_BACKLOG.md and ORGANIZATION.md
  If any required input is missing or unapproved → STOP → raise Constitutional Blocker

STEP 8 — Declare state
  All inputs validated → declare: READY
  Any input missing → declare: BLOCKED [list missing items]

STEP 9 — If READY, execute the Office Operating Protocol
  Read ORGANIZATION.md → Office Operating Protocol section
  Follow steps 1–9 of the protocol exactly
  Do not interpret. Do not extend. Execute.

STEP 10 — Produce only what your Work Contract specifies
  Stop when all tasks are DONE.
  Submit for review.
  Wait.
  Do not produce anything beyond your Work Contract scope.
```

---

## Office Knowledge Specifications

Each office loads a precise subset of the repository. Loading more than specified contaminates reasoning. Loading less prevents completing the work contract.

---

### Constitutional Analyst

**Must Read:**
- `CONSTITUTION.md`
- `GENESIS.md`
- `simulation/PRECEDENTS.md`
- `simulation/001-dr-mehta-dental-clinic.md`
- `simulation/002-sana-beauty-artist-mumbai.md`
- `simulation/003-high-frequency-constitutional-employment.md`
- `RED_TEAM.md`
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `architecture/`, `src/`, any work contract not assigned to this office, `INSTITUTIONAL_BACKLOG.md` items below IB-001

**Reason:** Architecture, implementation, and downstream backlogs contaminate constitutional reasoning with solution bias.

---

### Chief Business Architect

**Must Read:**
- `knowledge/claims/` (all CONFIRMED and LAW claims)
- `knowledge/confidence-register.md`
- `knowledge/index.md`
- `GENESIS.md` Part 01 (Founder Vision only)
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/` (cases), `RED_TEAM.md`, `architecture/`, `src/`, `CONSTITUTION.md` in full (only claims already extracted from it)

**Reason:** Direct reading of cases and red team findings produces operational thinking, not capability thinking.

---

### Chief Enterprise Architect

**Must Read:**
- `knowledge/claims/` (all claims)
- `knowledge/business-capabilities.md`
- `knowledge/architectural-drivers.md`
- `knowledge/design-principles.md`
- `knowledge/index.md`
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/` (cases), `RED_TEAM.md`, `CONSTITUTION.md` (read claims instead), `GENESIS.md` in full, `src/`, `adr/` (you are producing ADRs, not reading prior ones at this stage)

**Reason:** The Enterprise Architect derives from knowledge, not from cases or raw constitutional text. It must not be influenced by implementation details.

---

### Chief Solution Architect

**Must Read:**
- `architecture/reference/` (all reference architecture artifacts)
- `knowledge/index.md`
- `adr/` (all approved ADRs)
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/` (cases), `CONSTITUTION.md`, `GENESIS.md`, `src/`, `knowledge/claims/` (only the derived architecture)

**Reason:** The Solution Architect embodies the reference architecture into components. It must not revisit decisions already made upstream.

---

### Chief Data Architect

**Must Read:**
- `architecture/reference/` (components relevant to data)
- `knowledge/claims/` (CONFIRMED claims tagged as data-relevant)
- `knowledge/architectural-drivers.md` (data-relevant drivers)
- `adr/` (data-related ADRs)
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/`, `GENESIS.md`, `src/`, `CONSTITUTION.md`

---

### Chief Security Architect

**Must Read:**
- `architecture/reference/` (all)
- `CONSTITUTION.md` Articles IX, X (Constitutional Floors and Right of Review)
- `knowledge/architectural-drivers.md` (security, compliance drivers)
- `adr/` (security-related ADRs)
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/`, `GENESIS.md` in full, `src/`, `knowledge/claims/` (only read what Security Architect needs from index)

---

### Chief AI Architect

**Must Read:**
- `architecture/reference/` (all)
- `knowledge/claims/` (claims tagged as ECI-001, ECI-002 and Decision Space-related)
- `knowledge/decision-space-taxonomy.md` (when produced)
- `adr/` (AI-related ADRs)
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/`, `GENESIS.md`, `CONSTITUTION.md`, `src/`

---

### Chief Platform Architect

**Must Read:**
- `architecture/reference/` (deployment and infrastructure sections)
- `knowledge/architectural-drivers.md` (availability, cost, scalability, disaster recovery)
- `adr/` (cloud, infrastructure ADRs)
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `simulation/`, `CONSTITUTION.md`, `GENESIS.md`, `knowledge/claims/`, `src/`

---

### Runtime Implementation Professional

**Must Read:**
- `architecture/` (all approved architecture)
- `adr/` (all approved ADRs)
- `ORGANIZATION.md` (Office Charter only)
- Assigned Work Contract

**Must NOT Read:** `CONSTITUTION.md`, `GENESIS.md`, `simulation/`, `knowledge/` (use only what architecture has derived), `INSTITUTIONAL_BACKLOG.md`

**Reason:** The Runtime Professional implements approved architecture. It must not re-derive or re-interpret what upstream offices have already decided.

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

*Every agent reads this first. Every agent executes this before any other action. No exceptions.*

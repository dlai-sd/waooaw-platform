# WAOOAW Platform

---

## Repository Status

```
Founding Corpus v1           Status: Ratified
Version:                     0.19.0 — P2 complete: payment/GST tables, Fitness Studio, OAuth/retention, domain taxonomy (2026-07-09)
Current Epoch:               Epoch 1 — Employment
Current Gate:                G2-G4: PASSED | G5: Prerequisites met
                             ⛔ G5 CLEAR ≠ implementation authorized for any session
                             Implementation sprint requires explicit Founder authorization
Authorized Offices:          Runtime Professional (IB-009) — AWAITING FOUNDER AUTHORIZATION
Engineering Status:          Architecture COMPLETE
                             Agents approved: 3 (Digital Marketing v2.0, Trading, Agricultural Advisory)
                             Source code: Prerequisites met. Awaiting explicit Founder approval.
```

---

## Operating Commands

> These are the only commands needed to operate the full GitHub-grounded agent model.
> The constitutional framework handles all sequencing, validation, and governance.

### Development Environment

```bash
# Initial setup (one-time)
cp .env.example .env          # edit .env with real values
./scripts/setup.sh            # brings up the full local stack

# Get a local dev JWT for API testing
./scripts/get-dev-token.sh                     # prints access_token
./scripts/get-dev-token.sh --full              # prints full JSON response
export TOKEN=$(./scripts/get-dev-token.sh)
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/v1/employment/contracts
```

### Sprint Operations (Founder commands)

```bash
# ── Sprint Start ──────────────────────────────────────────────────────────────
# 1. Activate Product Owner (Office 11) — produces sprint plan
@copilot You are Product Owner. Produce Sprint Plan for Sprint N.

# 2. Founder approves sprint plan (comment on the sprint plan issue)
/approved

# ── Sprint Execution ──────────────────────────────────────────────────────────
# Create an issue using the IB Implementation template, then assign it:
# GitHub UI: Issues → New Issue → "IB — Implementation Task" → fill form → Assign to @copilot

# Or via CLI:
gh issue create --repo dlai-sd/waooaw-platform \
  --template "ib-implementation.yml" \
  --title "[IB-009] Foundation Implementation" \
  --assignee "@copilot" \
  --label "type:implementation,office:runtime-professional,sprint:1,gate:G5"

# ── Constitutional Review ──────────────────────────────────────────────────────
# After CI passes on a PR, request review (comment on the PR):
@copilot review this PR as the Enterprise Architect

# ── Raise a Constitutional Blocker ────────────────────────────────────────────
gh issue create --repo dlai-sd/waooaw-platform \
  --template "constitutional-blocker.yml" \
  --title "[CB-NNN] Missing input: ..." \
  --label "constitutional-blocker,priority:critical"
```

### Platform Status (Platform Delivery Tracker — Office 12)

```bash
# On-demand status report via GitHub Actions
gh workflow run pm-report.yaml --repo dlai-sd/waooaw-platform

# Narrative status report via Copilot (comment anywhere in GitHub)
@copilot You are Platform Delivery Tracker. Status report.

# View the live platform status issue
gh issue list --repo dlai-sd/waooaw-platform --label "platform-status"
```

### CI/CD Pipeline

```bash
# The pipeline runs automatically on PR and merge.
# To manually trigger the PM report:
gh workflow run pm-report.yaml

# View latest CCT results
gh run list --repo dlai-sd/waooaw-platform --workflow "promote.yaml" --limit 5

# View current image tags in GHCR
gh api /orgs/dlai-sd/packages/container/constitutional-engine/versions --jq '.[0:3]'
```

### Agent Label Reference

When creating GitHub Issues, use these labels to route agents correctly:

| Label prefix | Values | Purpose |
|---|---|---|
| `type:` | `implementation`, `architecture`, `constitutional-blocker`, `sprint-plan` | Issue category |
| `office:` | `runtime-professional`, `enterprise-architect`, `solution-architect`, `data-architect`, `platform-architect`, `security-architect`, `business-architect`, `constitutional-analyst` | Executing office |
| `component:` | `constitutional-engine`, `business-platform`, `professional-runtime`, `ai-runtime`, `web`, `infrastructure`, `platform-ops` | Component affected |
| `domain:` | `d1-hire`, `d2-govern`, `d3-execute`, `d4-authority`, `d5-terminate`, `d6-platform`, `d7-portal`, `d8-cs-agents`, `nfr-security`, `nfr-performance`, `nfr-cost`, `nfr-observability` | Capability domain |
| `gate:` | `G5`, `G5-parallel`, `G5-prerequisite`, `post-G5` | Gate authorization |
| `sprint:` | `sprint:1`, `sprint:2`, ... | Sprint number |
| `status:` | `waiting`, `in-progress`, `blocked`, `done`, `approved` | Current state |

---

## Repository Purpose

This repository does not exist to produce software.

It exists to discover, govern, derive, and embody the constitutional institution known as WAOOAW.

Software is one embodiment.

The institution is the enduring asset.

---

## What WAOOAW Is

> **WAOOAW is an institution that enables organizations to employ autonomous digital professionals under constitutional governance.**

WAOOAW stands for Ways Of Working for the Autonomous World.

---

## The Four Founding Discoveries

**Discovery 1 — Constitutional Governance**

The problem is not building autonomous systems. The problem is governing delegated professional judgment with legitimacy. This became the purpose of WAOOAW.

**Discovery 2 — Constitutional Discovery Engineering (CDE)**

Requirements are not invented. They are discovered through structured confrontation between reality and constitutional principles. This became the development methodology.

**Discovery 3 — Decision Space**

Decision Space is the constitutional primitive. Not actions. Not authority. Not employment. Everything else is a consequence of Decision Space. This became the architectural primitive.

**Discovery 4 — Institution Before Implementation**

The institution must exist before the software. Architecture exists to faithfully embody the institution — not define it. This became the engineering philosophy.

---

## The Engineering Method

> We do not begin with solutions.
>
> We begin with reality.
>
> We discover constitutional behavior through cases.
>
> We deliberate before we govern.
>
> We govern before we architect.
>
> We architect before we implement.
>
> We implement only what the institution has already earned.
>
> And when reality contradicts us, we change our understanding before we change our confidence.

---

## Naming Evolution

The vocabulary of WAOOAW evolved through Constitutional Discovery. Each name reflects a reduction toward a more fundamental abstraction.

```
Agent                 →  Digital Professional
Task                  →  Delegated Judgment
Permission            →  Licensed Decision Space
Employment            →  Delegation of Decision Space Occupancy
Trust Score           →  Trust Ledger
Simulation            →  Constitutional Discovery Case
Gap                   →  Constitutional Discovery
NFR                   →  Architectural Driver
Repository            →  Legal Record of the Institution
Architecture          →  Engineering Derivation of the Institution
Implementation        →  Embodiment
```

> **Vocabulary changes are constitutional events. New terminology shall not be introduced unless it reduces ambiguity or reveals a more fundamental abstraction than the term it replaces.**

---

## Current Institutional State

### Governing Documents

| Document | Purpose | Status |
|---|---|---|
| constitution/CONSTITUTION.md | The law. v1.2 — 17 Articles, 4 Amendments | Ratified |
| constitution/GENESIS.md | Engineering operating system. Parts 01–04 | Active |
| constitution/ORGANIZATION.md | Constitutional organization. 10 offices, 7 attributes each | Ratified — G1 ✓ |
| constitution/RED_TEAM.md | Constitutional Audit. 11 attacks. 0 failures | Complete |

### Constitutional Discovery Corpus

| Artifact | Constitutional Stress | Status |
|---|---|---|
| simulation/001 — Dr. Mehta Dental Clinic | Trust, lifecycle, shadow authority | Complete |
| simulation/002 — Sana Beauty Artist | Creative identity, seasonal employment | Complete |
| simulation/003 — High-Frequency Trading | Time, irreversibility, physics constraints | Complete |
| simulation/PRECEDENTS.md | CP-001 to CP-003 ratified; ECI-001, ECI-002 emerging | Active |

### Constitutional Confidence

```
Cases Executed:                 3
Constitutional Discoveries:    18
Precedents Ratified:            3
Constitutional Amendments:      4
Emerging Interpretations:       2
Under Deliberation:            15
Known Contradictions:           0
```

---

## Engineering Readiness

```
Gate G0   Institution                  ✓ Complete
Gate G1   Engineering Organization     ✓ Complete
Gate G2   Knowledge System             ○ Not Started
Gate G3   Reference Architecture       ⊘ Blocked (requires G2)
Gate G4   Technology Architecture      ⊘ Blocked (requires G3)
Gate G5   Reference Runtime            ✗ Prohibited
Gate G6   Reference Product            ✗ Prohibited
Gate G7   Marketplace                  ✗ Prohibited

Current Authorized Activity:
  Constitutional Analyst:  AUTHORIZED — produce knowledge claims (IB-001)
  All other offices:       WAITING — blocked by gate sequence
  Architecture work:       PROHIBITED until Gate G3
  Implementation work:     PROHIBITED until Gate G5
```

---

## What Comes Next — Epoch 2

The first Constitutional Office to become operational is the **Constitutional Analyst**.

Not a hire. An office activation.

The Constitutional Analyst processes the entire institutional corpus — Constitution, GENESIS, Cases, Precedents, Red Team — and produces typed, atomic, traceable claims in `knowledge/claims/`.

When Gate G2 passes — when the Enterprise Architect can derive reference architecture from knowledge without asking the Founder — Epoch 3 begins.

Architecture will be derived from knowledge. Technology will be derived from architecture. Runtime will be derived from technology. The software will be one embodiment of what the institution has already discovered.

---

## Governing Sequence

```
Constitution → GENESIS → Organization → Knowledge → Architecture → Implementation
```

No step may be skipped. No step may begin before the previous is approved.

---

*Founding Corpus v1 is ratified. The Constitutional Analyst is authorized to begin.*

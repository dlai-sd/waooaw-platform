# WAOOAW Steward Interface — Architecture Specification

**Version:** 1.0
**Date:** 2026-07-19
**Constitutional Basis:** C-001 (Human Override), C-002 (Trust through Evidence), C-064 (Three-Human Institution), C-066 (Authorization Tiers), C-068 (Steward Access Isolation — pending ratification)
**Status:** RATIFIED — C-068 and C-069 ratified 2026-07-19

---

## 1. Overview

The three human stewards (Yogesh, Sujay, Ojal) interact with the WAOOAW platform exclusively through **chat** — either on a purpose-built steward web interface or via WhatsApp. They never directly edit markdown files, raise GitHub Issues manually, or navigate the developer toolchain. All such actions are executed on their behalf by **WAOOAW AI Agent — Steward Assistant**.

This is not a limitation — it is the constitutional design. The stewards govern by intent and judgment; the platform executes by action and evidence.

---

## 2. Steward Entry Points

### 2.1 Web Interface (Primary)

| Property | Value |
|---|---|
| **URL** | `https://ops.waooaw.ai/` (separate subdomain) |
| **Auth** | Google OAuth via Keycloak `waooaw-steward` client |
| **Allowlist** | Exactly 3 Google accounts: yogesh@dlaisd.com · sujay@dlaisd.com · ojal@dlaisd.com |
| **Visibility** | NOT linked from waooaw.ai, NOT in sitemap.xml, NOT mentioned in any WhatsApp flow, NOT in robots.txt allow list |
| **UI** | Single-page chat interface — no dashboards, no forms, no navigation menus |
| **Session timeout** | 8 hours (steward sessions are long-lived, re-auth if idle >8h) |

### 2.2 WhatsApp (Secondary — same chat, different channel)

| Property | Value |
|---|---|
| **Access** | Dedicated WABA phone number (separate from customer-facing WABA) |
| **Auth** | WhatsApp OTP on first session + Keycloak phone bind to steward Google account |
| **Role detection** | Phone number bound to `steward` role in Keycloak — no password or PIN required after initial bind |
| **Feature parity** | Full — same Steward Assistant agent, same capabilities |

### 2.3 What Is Deliberately Excluded

- No link from `waooaw.ai` or any customer-facing page
- No QR code in any marketing material
- No mention in any WhatsApp welcome message to customers
- No reference in API docs, OpenAPI specs, or public repositories
- Google OAuth allowlist is enforced at Keycloak level — attempting to log in with any other Google account returns a generic 403 with no explanation of the steward system

---

## 3. WAOOAW AI Agent — Steward Assistant

### 3.1 Agent Identity

| Attribute | Value |
|---|---|
| **Designation** | WAOOAW AI Agent — Steward Assistant |
| **Type** | Internal governance agent |
| **Scope** | Platform governance, agent quality oversight, constitutional compliance, growth operations |
| **Does NOT serve** | Customers — entirely internal to the three human stewards |
| **LLM tier** | Always FRONTIER (bypasses ADR-024 tier routing — see ADR-028) |
| **Context window** | Full — loads all 67 constitutional claims, PROJECT_STATE.md, current ADR index, live platform data at session start |

### 3.2 Context Loaded at Every Session Start

```
1. constitution/CONSTITUTION.md          — immutable constitutional law
2. constitution/PROJECT_STATE.md         — current platform version + milestone status
3. knowledge/claims/C-001 to C-067       — all ratified claims (compact index via knowledge/index.md)
4. adr/ADR-INDEX.md                      — all architectural decisions
5. Live: GitHub Issues (open, awaiting approval)    — via GitHub API
6. Live: CCT pass rates (last 24h)                  — via Azure Monitor
7. Live: Cost vs C-067 ceilings                     — via Azure Cost Management API
8. Live: Agent performance (trust scores, C-049)    — via professional.trust_ledger query
9. Live: Constitutional Blocker status              — from blockers/ folder via GitHub API
```

### 3.3 Person-Aware Behavior

The session JWT contains `person: yogesh | sujay | ojal`. The Steward Assistant adapts its proactive surface:

| Person | Proactive Opening (at session start) |
|---|---|
| **Yogesh** | Open approvals queue count · Any P0-Constitutional incidents since last session · Cost vs ceiling status · Active Constitutional Blockers |
| **Sujay** | Agents below Grade B (last 7 days) · C-049 escalation count per agent type · Trial-to-paid conversion rate this week · Any new competitive intelligence flagged by Self-Improvement Analyst |
| **Ojal** | C-048 events (exploitation detection, if any) · C-049 spike alerts · Claims overdue for review · Any active Constitutional Blockers filed since last session |

### 3.4 Capabilities by Request Category

| What steward says | What Steward Assistant does |
|---|---|
| "Show me Sujay's DMA performance this week" | Queries `professional.trust_ledger` + `constitutional.audit_records`, formats as chat summary |
| "I want to improve DMA Skill 3 prompt" | Loads current prompt from `professional.agent_prompts`, proposes rewrite in chat, runs simulation against AS-001, shows Grade, awaits approval |
| "Submit that improvement" (after review) | Creates branch `agent/update/dma-skill3-prompt-v2`, commits updated `.md` file, opens GitHub PR with correct labels, notifies Yogesh if Tier 3 needed |
| "How much did we spend this month?" | Queries Azure Cost Management API, compares to C-067 ceilings, flags any environment at >80% |
| "File a Constitutional Blocker on CE Emergency Stop" | Fills in form from conversation context, creates `blockers/CB-NNN-yogesh-2026-07-19.md`, opens GitHub Issue with constitutional-blocker template, requests changes on related PR |
| "What's the approval queue?" | Lists all GitHub Issues with `awaiting:founder-approval` label, allows Yogesh to say "approve #47" → posts `/approved` comment via GitHub API |
| "Generate this week's compliance report" | Queries C-048/C-049 audit records, formats report, commits to `reviews/R-NNN-compliance-ojal-YYYY-MM-DD.md` via GitHub API |
| "Is the platform safe to take a new customer today?" | Checks: CCT pass rate 100%? No active P0? No active Constitutional Blockers? Cost below ceiling? Returns go/no-go with evidence |

### 3.5 What the Steward Assistant Will NOT Do

- Merge its own PRs (C-065 — self-merge prohibited, always requires reviewer)
- Modify `constitution/CONSTITUTION.md` or `constitution/GENESIS.md` (Class 1 Immutable)
- Execute Tier 3 actions without Yogesh confirmation in the same session
- Give a steward access to another steward's private session history
- Impersonate a customer or access customer data beyond what is required for the stated governance purpose (C-048)

---

## 4. GitHub API Writeback — How Platform Changes Are Recorded

Every action taken via the Steward Assistant that changes platform state is committed to the GitHub repository. The steward portal is a GitHub API client — the repo remains the single source of truth.

### 4.1 Writeback Mechanism

```
Steward intent (chat)
  → Steward Assistant constructs GitHub API payload
  → Uses WAOOAW GitHub App token (not steward's personal token)
  → Creates branch → commits file(s) → opens PR
  → PR contains: conventional commit message + constitutional basis + IB reference
  → CI runs (constitutional commit gate + C-066 tier check)
  → Reviewer approves (Yogesh for Tier 3, Sujay for Tier 1/2)
  → Merge → deployment pipeline triggers
```

### 4.2 Files Written by Each Action Type

| Action | Files Created/Updated | Branch Convention |
|---|---|---|
| Prompt improvement | `architecture/reference/prompts/{agent}-prompts.md` + DB seed | `agent/update/{agent}-skill-{n}-prompt-v{N}` |
| New Skill Proposal | GitHub Issue only (no file until approved) | N/A — issue only |
| Constitutional Blocker | `blockers/CB-NNN-{office}-{date}.md` | `constitutional/blocker/CB-NNN` |
| New constitutional claim | `knowledge/claims/C-0NN.md` + `knowledge/index.md` | `constitutional/claim/C-0NN` |
| Compliance report | `reviews/R-NNN-compliance-ojal-{date}.md` | `chore/compliance-report-{date}` |
| PROJECT_STATE.md update | `constitution/PROJECT_STATE.md` | Current sprint branch |

### 4.3 Audit Trail

Every GitHub API call made by the Steward Assistant is logged to `constitutional.audit_records` with:
- `actor: yogesh | sujay | ojal`
- `action: github_commit | github_issue_create | github_pr_open`
- `evidence_key: {PR URL or Issue URL}`
- `constitutional_basis: C-065` (SDLC traceability)

---

## 5. Prompt Lifecycle — From Sujay's Chat to Production

The `.md` files are the human-readable source of truth. They never go into the container image. They seed the database during CI/CD.

```
Step 1: Sujay in chat
  "I want stronger CTA in DMA Skill 3 for Instagram Reels"

Step 2: Steward Assistant
  - Loads professional.agent_prompts WHERE agent_type='DMA' AND skill_id=3 AND is_active=true
  - Displays current prompt text in chat
  - Proposes improved version based on Sujay's direction

Step 3: Sujay reviews → "Run simulation"
  - Steward Assistant triggers AI Runtime simulation endpoint
  - Runs against AS-001 (Dr. Mehta acceptance scenario)
  - Returns Grade (A/B/C) + evidence

Step 4: Sujay approves Grade A result
  - Steward Assistant calls GitHub API:
    → Updates architecture/reference/prompts/dma-agent-prompts.md
    → Commits: "agent(spec): DMA Skill 3 Instagram Reels CTA - Grade A simulation v4"
    → Opens PR with labels: type:agent-update, update-type:new-prompt, approved:sujay

Step 5: CI pipeline on PR merge
  - seed-prompts.py reads .md file
  - INSERT INTO professional.agent_prompts (agent_type, skill_id, prompt_text, version, sha, simulation_grade)
  - Old version: is_active = false, retired_at = NOW()
  - New version: is_active = true

Step 6: AI Runtime (container — no prompt content)
  - At request time: SELECT prompt_text FROM professional.agent_prompts
    WHERE agent_type='DMA' AND skill_id=3 AND is_active=true
  - Constitutional Engine records which prompt version (sha) was used in audit_records
```

**Security properties of this pipeline:**
- Container image contains zero prompt content — only Python code
- Prompt text at rest: encrypted by Azure PostgreSQL Transparent Data Encryption (automatic)
- Prompt text in transit: TLS 1.3 (DB connection) + VNet private endpoint (no public exposure)
- Prompt version auditable: every agent session records `prompt_sha` in `constitutional.audit_records`
- Rollback: set previous version `is_active=true` via one DB update — no redeployment needed

---

## 6. AI API Tier Access: Stewards vs Customers

See ADR-028 for full decision record. Summary:

| Access Class | JWT Claim | LLM Routing |
|---|---|---|
| **Steward** | `role: steward` | Always FRONTIER — bypasses ADR-024 classification gate |
| **Customer Essential** | `plan_tier: essential` | LOCAL (70%) + MID_TIER (30%), no FRONTIER |
| **Customer Professional** | `plan_tier: professional` | MID_TIER (60%) + FRONTIER (40%, capped per C-051) |
| **Customer Enterprise** | `plan_tier: enterprise` | FRONTIER preferred, LOCAL for classification only |
| **Internal Platform Agents** | `role: platform-agent` | MID_TIER default, FRONTIER for constitutional evaluation |

The AI Runtime LLM Gateway reads `role` from JWT first. If `role=steward`, dispatch to FRONTIER unconditionally. Otherwise, read `plan_tier` and apply ADR-024 tier routing.

---

## 7. Gap Registry — Identified During This Review

| ID | Gap | Severity | Resolution |
|---|---|---|---|
| **G-INSTINCT-01** | CE `ValidateAction` returns stub AUTHORIZED — constitution not enforced at runtime | P0 | Implement claim evaluators for runtime-enforceable claims (C-041, C-043, C-048, C-049, C-051, C-062) |
| **G-INSTINCT-02** | Constitutional claim amendments not automatically reflected in CE logic | P1 | Claim evaluators registered by claim ID — amending C-043.md triggers evaluator update review |
| **G-INSTINCT-03** | CCTs run only at deploy time — live agents can drift between deploys | P1 | Add scheduled CCT run (every 6h) in production Temporal workflow |
| **G-INSTINCT-04** | No automatic performance gap detection — waits for Sujay to observe | P1 | WAOOAW AI Agent — Self-Improvement Analyst (nightly Temporal workflow) |
| **G-INSTINCT-05** | C-049 escalation patterns not read to generate improvement proposals | P1 | Part of Self-Improvement Analyst scope |
| **G-INSTINCT-06** | Platform cannot self-propose improvements — purely reactive | P1 | Self-Improvement Analyst raises Skill Proposals automatically |
| **G-INSTINCT-07** | No `professional.agent_prompts` table — prompts have no DB versioning | P0 | Required for secure prompt deployment pipeline (Section 5 above) |
| **G-INSTINCT-08** | Trust ledger referenced in README but no data structure defined | P1 | Design `professional.trust_ledger` table (Section of this doc) |
| **G-INSTINCT-09** | Autonomy flat — track record does not expand agent authorization | P2 | Trust score → autonomy tier escalation after 30 sessions at ≥0.95 |
| **G-INSTINCT-10** | Steward-autonomous boundary undefined — when can platform act vs ask | P1 | C-068 + Steward Assistant capability boundary (Section 3.5) |
| **G-INSTINCT-11** | No `plan_tier` claim in customer JWT (ADR-003 gap) | P0 | ADR-003 amendment + ADR-028 |
| **G-STEWARD-01** | `ops.waooaw.ai` steward subdomain needs Terraform + Keycloak client config | P1 | Terraform module addition + Keycloak realm update |
| **G-STEWARD-02** | `professional.agent_prompts` table missing from DB migration scripts | P0 | New migration: `07-agent-prompts.sql` |
| **G-STEWARD-03** | `seed-prompts.py` CI step missing from GitHub Actions | P0 | Add to `ci.yaml` post-migration step |
| **G-STEWARD-04** | WAOOAW AI Agent — Self-Improvement Analyst not specced | P1 | New agent specification required (IB item) |
| **G-STEWARD-05** | WAOOAW AI Agent — Steward Assistant not specced as formal agent | P1 | This document is the spec — needs AGENT-AUTHORING-GUIDE validation |

---

## 8. New Constitutional Claims Required

### C-068 — Steward Access Isolation (DRAFT — pending Yogesh ratification)

```
Type:       ARCHITECTURAL CONSTRAINT
Statement:  The steward interface is cryptographically separated from the customer
            portal. A customer JWT cannot be elevated to steward access. The steward
            entry URL is not published, not indexed, and not reachable via any
            customer-facing flow. Steward identity is verified by Google OAuth
            allowlist enforced at Keycloak level. Any system change that would make
            the steward entry point discoverable from a customer session is a
            Class 2 constitutional violation.
Depends On: C-001 (Human Override — stewards must have unobstructed access),
            C-064 (Three-Human Institution — only these three may have steward access)
```

### C-069 — Platform Self-Improvement Obligation (DRAFT — pending Yogesh ratification)

```
Type:       OBLIGATION
Statement:  The platform has a constitutional obligation to monitor its own
            constitutional compliance and professional output quality, and to
            generate improvement proposals when degradation is detected. Degradation
            is defined as: any agent skill with ≥3 C-049 escalations in 7 days,
            any simulation grade below A for a previously Grade-A skill, or any
            CCT failure in production. Improvement proposals must be raised as
            Skill Proposals within 24 hours of detection and routed to Sujay.
            Waiting for a human to notice a quality drop before acting is a
            violation of this obligation.
Depends On: C-049 (Honest Limitation), C-002 (Trust through Evidence),
            C-023 (Evidence First — evidence of degradation must precede the proposal)
```

---

*This document is owned by WAOOAW AI Agent — Platform IT Expert.*
*Review authority: Yogesh Khandge (constitutional sections) · Sujay Khandge (agent quality sections) · Ojal Khandge (compliance sections)*
*Next action: Yogesh to ratify C-068 and C-069 via `/approved` on the PR that introduces this file.*

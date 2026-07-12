# EA Review: PR #5 (C-053 SIL + C-054 SIR) and PR #6 (C-055 Campaign Theme Engine)

**Reviewer:** Enterprise Architect
**Date:** 2026-07-12
**Session:** PR Critical Review + Merge Sequence
**PRs Reviewed:** #5 (arch/signal-skill-intelligence-c053-c054) · #6 (arch/campaign-theme-engine-c055)

---

## Constitutional Claim Quality Assessment

### C-053 — Signal Sensing Obligation
**Type:** LAW ✓ | **Confidence:** 94% ✓ | **Dependencies:** correct ✓
**Finding:** `Produces` field references `institutional.signal_watch_log` — this table does NOT exist in SQL; only `institutional.signal_materiality_events` was created. Minor inconsistency in claim metadata.
**Verdict:** APPROVED with fix required (R5-F1)

### C-054 — Skill Intelligence Routing
**Type:** LAW ✓ | **Confidence:** 93% ✓ | **Dependencies:** correct ✓
**Finding:** Claim states it "Produces" `business.agent_skill_graph SQL table` — table is created ✓. Constitutional chain from C-036→C-050→C-054 is sound.
**Verdict:** APPROVED

### C-055 — Campaign Coherence Obligation
**Type:** LAW ✓ | **Confidence:** 95% ✓ | **Dependencies:** correct ✓
**Finding:** Strong claim. The extension of C-044 (Synthetic Approval) to content quality is constitutionally sound — customer approves the review criteria, not each post. SCR Check 3 (Compliance) mandatory routing to customer is a constitutional protection, correctly stated.
**Verdict:** APPROVED

---

## Architecture Chain Update Findings

### PR #5 — Gaps (GATE BLOCKERS)

| # | Gap | File Missing | Severity | Fix Ref |
|---|---|---|---|---|
| R5-F1 | `C-053.md` Produces field references non-existent `signal_watch_log` table | knowledge/claims/C-053.md | MINOR | R5-F1 |
| R5-F2 | `AGENT-ENTRY.md` not updated — version still 0.31.0, agents still at pre-PR5 versions | constitution/AGENT-ENTRY.md | GATE BLOCKER | R5-F2 |
| R5-F3 | `business-capabilities.md` — no new sub-capabilities for Signal Sensing (Domain 12) or Skill Intelligence Routing (cross-domain) | knowledge/business-capabilities.md | GATE BLOCKER | R5-F3 |
| R5-F4 | `capability-to-container-map.md` — SIL/SIR capabilities not mapped to AI Runtime | architecture/reference/capability-to-container-map.md | GATE BLOCKER | R5-F4 |
| R5-F5 | `institutional.agent_prompt_versions` seeds missing for 7 new prompts (SIR x3, SIL x3 + SKILL_INTENT_ROUTER) — Activation Gate Section 2.3 FAIL | infrastructure/postgres/init/03-enums-and-tables.sql | GATE BLOCKER | R5-F5 |
| R5-F6 | Trading agent Section 3.18 (Signal Intelligence) and Section 3.19 (SIR/SCMs) not added | architecture/reference/agents/trading-agent.md | P1 — deferred, tracked below | — |

### PR #6 — Gaps (GATE BLOCKERS)

| # | Gap | File Missing | Severity | Fix Ref |
|---|---|---|---|---|
| R6-F1 | `AGENT-ENTRY.md` not updated — DMA still v2.1, Activation Gate still 10 sections | constitution/AGENT-ENTRY.md | GATE BLOCKER | R6-F1 |
| R6-F2 | `GENESIS.md` — DMA entry still v2.0; must be v2.5 after Campaign Theme Engine upgrade | constitution/GENESIS.md | GATE BLOCKER (NEVER SKIP) | R6-F2 |
| R6-F3 | `business-capabilities.md` — no new Campaign sub-capabilities under Domain 11 | knowledge/business-capabilities.md | GATE BLOCKER | R6-F3 |
| R6-F4 | `capability-to-container-map.md` — Campaign Theme Engine (AI Runtime) not mapped | architecture/reference/capability-to-container-map.md | GATE BLOCKER | R6-F4 |
| R6-F5 | `containers.md` — youtube-mcp, linkedin-mcp, x-mcp, pinterest-mcp, threads-mcp referenced in Section 3.21 but not in MCP inventory — Activation Gate Section 3.1 FAIL | architecture/reference/containers.md | GATE BLOCKER (with caveat — see note) | R6-F5 |
| R6-F6 | `institutional.agent_prompt_versions` seeds missing for 7 new campaign prompts — Activation Gate Section 2.3 FAIL | infrastructure/postgres/init/03-enums-and-tables.sql | GATE BLOCKER | R6-F6 |
| R6-F7 | AGENT-AUTHORING-GUIDE conflict — PR #6 gate adds Section 14 from base of 11; after PR #5 merges (gate = 13), PR #6 must add Section 14 to gate of 13 (not 11) | architecture/reference/agents/AGENT-AUTHORING-GUIDE.md | MERGE CONFLICT | R6-F7 |

**Note on R6-F5:** New platforms (YouTube, LinkedIn, X, Pinterest, Threads) are declared with `dependency_status: PENDING_FOUNDER_ACTION` in the agent spec. The correct resolution is to add them to containers.md with status `PLANNED — awaiting Founder authorization` rather than blocking the spec. The MCP Gate (Section 3.1) applies to ACTIVE MCPs; PLANNED MCPs are acceptable as long as the dependency status is documented. However, containers.md must still contain the entry.

---

## Approved Architecture Decisions Assessment

### AD-026 — Signal Watch Workflow Pattern
**Type:** HARD (for CRITICAL) / Soft (ADVISORY) ✓ — correct split
**Finding:** `continue_as_new` at 1,000 poll cycles correctly documented.
**Verdict:** APPROVED

### AD-027 — Skill Capability Manifest Standard
**Finding:** Required SCM fields complete. The gap: Activation Gate Section 4 (Skill Runtime Gate) check 4.1 references "Section 3.14 equivalent exists" — but the new Section 4 check (13.2) only checks SCM existence, not Section 3.14 presence. These are distinct. No conflict.
**Verdict:** APPROVED

### AD-028 — Campaign Theme Cascade Standard
**Finding:** CE.ValidateAction gate on `scr_status IN ('SCR_PASSED', 'CUSTOMER_APPROVED')` is constitutionally sound — publishing without SCR is prevented at the CE level, not just application level. ✓
**Verdict:** APPROVED

---

## Design Principles Assessment

### DP-022, DP-023, DP-024
All three are correctly structured with Directive → Why → Constitutional Basis → Enforcement. Enforcement sections are specific and auditable. ✓

---

## SQL / Data Architecture Assessment

**PR #5:**
- `institutional.signal_materiality_events`: no tenant_id (correct — platform-wide, no PII). ✓
- `institutional.skill_gap_signals`: has organisation_id + tenant-scoped INSERT RLS. However: has `unserviced_intent TEXT NOT NULL` — this field could contain PII if the customer typed their name into a message that went unrouted. **Gap:** intent text should be passed through VTL (anonymisation) before storage. Minor — but important for GDPR/DPDP compliance.
- `business.agent_skill_graph`: pgvector index `WITH (lists = 100)` — correct for production scale. ✓

**PR #6:**
- `business.content_campaigns`: `theme_sequence JSONB NOT NULL` — the sequence is generated before the campaign is approved. Should allow NULL until ACTIVE status. **Gap:** constraint too strict for DRAFT → APPROVED flow.
- `business.scr_review_records`: correctly prevents UPDATE/DELETE (constitutional audit artifact). ✓
- `content_scr_status` enum: PUBLISH_FAILED is an important operational state. ✓

---

## Activation Gate Assessment (both PRs combined, when merged)

| Section | Status | Note |
|---|---|---|
| 1 — Spec Completeness | PASS | |
| 2 — Prompt Gate | FAIL | Missing `agent_prompt_versions` seeds for 14 new prompts total |
| 3 — MCP Gate | PASS (with noted PLANNED entries for PR #6 platforms) | |
| 4 — Skill Runtime Gate (new SCMs) | PASS | |
| 5 — Execution Loop Gate | PASS | SignalWatchWorkflow pattern documented |
| 6 — Data Gate | PASS (with minor note on skill_gap_signals anonymisation) | |
| 7 — Constitutional Gate | PASS | |
| 8 — Architecture Chain Gate | FAIL | AGENT-ENTRY, GENESIS, business-capabilities, capability-map missing |
| 9 — Review Gate | PENDING | This review creates the record |
| 10 — Cognition Gate | PASS | |
| 11 — Token Economy Gate | PASS | |
| 12 — Signal Intelligence Gate | PASS | |
| 13 — SIR Gate | PASS | |
| 14 — Campaign Theme Engine Gate | FAIL (pending fix R6-F6) | Prompts not seeded |

---

## P1 Open Items (Not Gate Blockers — tracked)

1. **Trading agent Sections 3.18 + 3.19** — No Signal Intelligence or SCMs added to Trading agent spec. Required before Trading IB-009 sprint. Tracked as P1.
2. **`skill_gap_signals.unserviced_intent` anonymisation** — Intent text may contain PII. Should add anonymisation step before DB insert. P2 — track for implementation sprint.
3. **`content_campaigns.theme_sequence` NULL constraint** — Too strict for DRAFT state. Fix: allow NULL, enforce NOT NULL only at ACTIVE status transition (application-level, not DB constraint).
4. **X (Twitter) platform decision** — $100/month. Awaiting Founder decision. Dependency register item.
5. **PR #5 + PR #6 on-main: `architecture/reference/containers.md` MCP server count** — New platform MCPs (youtube-mcp etc.) need PLANNED entries.

---

## Merge Verdict

**PR #5:** APPROVED pending 5 fixes (R5-F1 through R5-F5)
**PR #6:** APPROVED pending 7 fixes (R6-F1 through R6-F7) + rebase onto merged PR #5

**Merge sequence:** Fix PR #5 → Merge PR #5 → Rebase + Fix PR #6 → Merge PR #6

---
*Review produced by: Enterprise Architect*
*Constitutional Basis: C-047 (evidence-first — review record before any merge action)*

# R-014 — Enterprise Architect Review: Digital Marketing Agent v2.0 + Architecture Chain

**Review ID:** R-014
**Reviewer Office:** Enterprise Architect
**Subject:** Digital Marketing Agent v2.0 + full Architecture Chain (IB-005 → IB-008)
**Files reviewed:**
- `architecture/reference/agents/digital-marketing-agent.md` (v2.0)
- `knowledge/claims/C-043.md` (new)
- `knowledge/business-capabilities.md` (Domain 11 addition)
- `knowledge/architectural-drivers.md` (AD-016 addition)
- `knowledge/design-principles.md` (DP-014 addition)
- `architecture/reference/containers.md` (MCP inventory expansion)
- `architecture/reference/components/ai-runtime.md` (Pipelines 6 + 7)
- `infrastructure/postgres/init/03-enums-and-tables.sql` (5 new tables)
- `docker-compose.yml` (MCP service env vars)
**Date:** 2026-07-09

---

## Overall Verdict: APPROVED WITH NOTES

The v2.0 expansion is constitutionally grounded, architecturally consistent with the existing 4-container model, and correctly derives from the claims corpus. The new skills, phase bundle model, AI-native profiling pipeline, and data architecture are all sound. Four findings require resolution before activation; three are mechanical fixes; one (docker-compose stub services) is a P0 that must be resolved for the local environment to be usable.

All P1 findings have been addressed within this review session. P2 items are noted for the implementation sprint.

---

## 1. Constitutional Traceability Verification

### New Claims

| Claim | Type | Derives From | Verdict |
|---|---|---|---|
| C-043 — Financial Spend Authority Ceiling | LAW | C-003, C-041 | ✓ SOUND — derivation is correct; financial spend authority is a bounded license under C-003 Second Law |

**Note R014-01 (fixed in session):** C-043's `Produces` field incorrectly listed DP-014. DP-014 concerns maturity-driven skill activation, not financial spend. Corrected to: `Produces: AD-016` only.

### New Claims Traceability to New Skills

| Claim | Skills That Depend On It | Correctly Referenced |
|---|---|---|
| C-043 | Skill 11 (Paid Advertising) | ✓ BUDGET_OVERRUN in prohibited actions |
| C-039 | Skill 0 (Customer Profiling) | ✓ AI-native conversational interface |
| C-040 | Skills 1, 10, 13 | ✓ Domain specialization cited per skill |
| C-041 | All skills with MCP tools | ✓ Every MCP tool has Decision Space authorization entry |
| DP-014 | Phase bundle gating | ✓ phase_prerequisite in Professional Template |

---

## 2. Capability-to-Container Mapping — Domain 11

New capabilities mapped to existing containers. No new container required. ✓

| Capability | Owning Container | Supporting Containers |
|---|---|---|
| **11.1 Profile Customer** | AI Runtime (profiling pipeline) | Business Platform (profile storage via customer-profile-mcp) |
| **11.2 Maturity Assessment** | AI Runtime (market research pipeline) | Business Platform (score + heatmap storage) |
| **11.3 Social Content Execution** | Professional Runtime (execution) | AI Runtime (content creation + MCP publishing), CE (evidence per action) |
| **11.4 Local SEO + Reputation** | Professional Runtime | AI Runtime (seo-mcp, google-places-mcp, web-scan-mcp), CE (evidence) |
| **11.5 Paid Advertising** | Professional Runtime | AI Runtime (meta-ads-mcp, google-ads-mcp), CE (budget enforcement via ValidateAction + C-043) |
| **11.6 CRO + Competitive Intelligence** | Professional Runtime | AI Runtime (web-optimisation-mcp, social-profile-mcp, meta-ad-library-mcp), CE (evidence) |

All 6 Domain 11 capabilities fit within the existing 4-container architecture. ✓

---

## 3. Architecture Chain Completeness

| Layer | File | Status | Finding |
|---|---|---|---|
| Claims | C-043.md | ✓ with fix | R014-01: Produces field corrected |
| Capabilities | Domain 11 (6 caps) | ✓ | Clean. All capabilities cite AS/Claims |
| Drivers | AD-016 | ✓ | HARD type justified. 5-step enforcement pipeline specified |
| Principles | DP-014 | ✓ | Enforcement section complete. CE phase_prerequisite constraint specified |
| Containers | MCP inventory (23 servers) | ✓ with note | R014-02: social-profile-mcp description clarified (see below) |
| Component spec | ai-runtime.md Pipelines 6+7 | ✓ with fix | R014-03: CE.ValidateAction step added to Market Research Pipeline |
| Data schema | 5 new tables | ✓ with P2 note | Schema sound; enum types flagged for production (P2) |
| Docker Compose | env URLs added | ✗ P0 fixed | R014-04: stub service definitions were missing; added in session |
| GENESIS | AS-001, AS-002 still cover target personas | ✓ | No new AS required |
| AGENT-ENTRY | Not yet updated | P2 | Address in next session |
| capability-to-container-map | Not updated | P2 fixed | Added Domain 11 in session |

---

## 4. Findings

### R014-01 — C-043 Produces Field (P1 — fixed in session)

**Finding:** `C-043.md` listed `Produces: AD-016, DP-014`. DP-014 is about maturity-driven skill activation, which derives from the Digital Marketing Agent design pattern — not from the financial spend claim.

**Fix applied:** C-043 `Produces` corrected to `AD-016` only.

---

### R014-02 — social-profile-mcp Authentication Ambiguity (P1 — fixed in session)

**Finding:** The `social-profile-mcp` container description stated "Instagram/Facebook public API endpoints, no auth." Instagram's Graph API requires OAuth authentication for most profile data. The Market Research constitutional constraint prohibits authenticated access. These are irreconcilable unless the server uses a public-search approach (not the Graph API).

**Architectural principle at stake:** Market Research (Skill 1) and Competitive Intelligence (Skill 13) are authorized only to access publicly available data. An MCP server that uses authenticated Graph API calls violates this constraint even if the data is nominally "public." The prohibition is on authenticated access attempts, not just on private data retrieval — because an authenticated call creates a relationship with the platform that is not authorized under C-041 without customer consent.

**Fix applied:** Container description updated in containers.md. `social-profile-mcp` now correctly states: "Public social profile data via web search and public page scraping (no platform API authentication); uses web-search-mcp pattern internally for social profile discovery."

**Residual note for implementation sprint:** When implementing `social-profile-mcp`, the engineering team must NOT use the Instagram Graph API. Public profile data must be retrieved via web search or publicly accessible profile URLs only.

---

### R014-03 — Market Research Pipeline Missing CE.ValidateAction Steps (P1 — fixed in session)

**Finding:** The Market Research Pipeline in `ai-runtime.md` did not show `CE.ValidateAction` calls before MCP tool invocations. C-041 states: *"Every external tool call made by a Digital Professional must be explicitly authorized."* The existing Trading PAAS pipeline documentation shows CE.ValidateAction as an explicit step. Inconsistency in documentation creates implementation risk.

**Fix applied:** `CE.ValidateAction(tool, decision_space)` step added to the Market Research Pipeline processing steps in ai-runtime.md, before each MCP tool invocation group.

---

### R014-04 — docker-compose Stub Services Missing (P0 — fixed in session)

**Finding:** The docker-compose update added 18 MCP service URL env vars (ports 8105–8122) to the ai-runtime environment block, but added ZERO stub service definitions. The compose file referenced services (`scheduling-mcp`, `instagram-mcp`, etc.) that did not exist as compose services → the local environment would fail to start with "service not found" errors for all new MCP URLs.

**Fix applied:** 18 stub service definitions added to docker-compose.yml (ports 8105–8122). All stubs follow the established pattern: Python/FastAPI stub with `/health`, `/tools`, and `/call/{tool_name}` endpoints.

---

### R014-05 — PATIENT_IMAGE_CONSENT_CONFIRMED Still Unresolved (P1 — fixed in session)

**Finding:** R-011 Note R011-01 required `PATIENT_IMAGE_CONSENT_CONFIRMED` to be added to always-ask actions in Skills 2 and 6 (now renumbered to Skills 4 and 8 in v2.0). The v2.0 constitutional checklist carries this as an unchecked item. After two spec versions this must be closed.

**Fix applied:** `PATIENT_IMAGE_CONSENT_CONFIRMED` added to always-ask in Skill 4 (Instagram) and Skill 8 (Video & Visual Content) in digital-marketing-agent.md.

---

## 5. P2 Findings (address before implementation sprint — not blocking spec activation)

### R014-P2-01 — PRODUCES_RECORD Execution Model Not Formally Defined

Skills 0 and 1 use `PRODUCES_RECORD` as their execution model. The existing execution model enum is `APPROVAL_GATE` / `PRE_AUTHORIZED`. `PRODUCES_RECORD` is a new pattern — an intelligence skill that produces an artifact (profile document, maturity report) rather than executing a channel action.

**Recommendation:** Add `PRODUCES_RECORD` as a third enum value to the `execution_model` enum in `03-enums-and-tables.sql`, and document it in the Professional Template section of the agent spec with a formal definition: *"Skill executes autonomously to produce an artifact; artifact is confirmed by the customer before becoming authoritative; no external platform action is taken until confirmation."*

---

### R014-P2-02 — SQL VARCHAR Instead of ENUM for need_state, bundle, profile_status

Three fields in the new tables use VARCHAR where the schema pattern uses ENUM:
- `digital_marketing_needs_heatmap.need_state` (8 fixed values)
- `dm_phase_bundle_subscriptions.bundle` (3 fixed values)
- `digital_marketing_profiles.profile_status` (3 fixed values)

**Recommendation:** Add three new ENUMs to `03-enums-and-tables.sql` before the implementation sprint: `digital_marketing_need_state`, `dm_phase_bundle`, `dm_profile_status`.

---

### R014-P2-03 — CE Interface Extension for Budget Parameters Not Documented

AD-016 states: *"CE.ValidateAction must carry budget state as a first-class parameter for spend-type tool calls."* This is an extension to the CE's existing gRPC interface. The CE component spec does not yet reflect this change, and no ADR exists for the interface extension.

**Recommendation:** Before the implementation sprint for Skill 11 (Paid Advertising), either:
(a) Update the CE component spec to add a `BudgetContext` parameter to the `ValidateAction` request, or
(b) Create ADR-021 documenting the CE interface extension for financial spend authorization.

---

### R014-P2-04 — capability-to-container-map.md (fixed in session)

Not updated with Domain 11 capabilities per AGENT-AUTHORING-GUIDE Section 13. Fixed in this session — Domain 11 rows added.

---

## 6. Architectural Soundness Assessment

### Phase Bundle Model (DP-014)

The maturity-driven activation model is architecturally correct. The critical design decision — that phase bundle upgrades require a new customer authorization event (recorded as a CE evidence record via `customer_authorization_event` FK in `dm_phase_bundle_subscriptions`) — correctly implements C-003 Second Law: authority expansion requires a new licensing event, not automatic promotion.

### Budget Enforcement (C-043 → AD-016)

The enforcement chain is sound: C-043 (claim) → AD-016 (driver, 5-step enforcement) → Skill 11 Decision Space (BUDGET_OVERRUN in prohibited actions) → `dm_phase_bundle_subscriptions` (phase activation evidence) → CE.ValidateAction extended with budget context. The chain is complete. The remaining gap (P2-03) is documentation of the CE interface, not the architectural decision itself.

### AI-Native Profiling vs. Conversational Configuration Engine

The Customer Profiling Pipeline (ai-runtime.md, Section 6) is architecturally distinct from the Conversational Configuration Engine (Section 5). The CCE produces a `DecisionSpaceInput` for Business Platform to commit. The Customer Profiling Pipeline produces a `CustomerProfile` record written directly to `customer-profile-mcp`. These are different artifacts with different ownership. The distinction is correctly modelled — the profile is Tier 2 customer-private data, not configuration.

### Data Tenant Isolation

All 5 new tables reference `organisation_id` with FK to `business.organisations`. The existing Row-Level Security policy on PostgreSQL (AD-004, DP-007) applies to these tables via organisation_id. No new RLS policy is required — the existing pattern covers the new tables.

---

## 7. Architecture Chain Update Summary (for PR)

| Layer | File | Change | Status |
|---|---|---|---|
| Claims | `knowledge/claims/C-043.md` | New LAW: Financial Spend Authority Ceiling | ✓ R014-01 fixed |
| Capabilities | `knowledge/business-capabilities.md` | Domain 11: 6 capabilities | ✓ |
| Drivers | `knowledge/architectural-drivers.md` | AD-016 | ✓ |
| Principles | `knowledge/design-principles.md` | DP-014 | ✓ |
| Containers | `architecture/reference/containers.md` | 18 MCP servers added | ✓ R014-02 fixed |
| Component spec | `architecture/reference/components/ai-runtime.md` | Pipelines 6+7 | ✓ R014-03 fixed |
| Data schema | `infrastructure/postgres/init/03-enums-and-tables.sql` | 5 new tables | ✓ (P2-01/02 deferred) |
| Docker Compose | `docker-compose.yml` | 18 stub services | ✓ R014-04 fixed |
| Capability map | `architecture/reference/capability-to-container-map.md` | Domain 11 | ✓ fixed |
| Agent spec | `architecture/reference/agents/digital-marketing-agent.md` | v2.0 | ✓ R014-05 fixed |

**Verdict: APPROVED — all P0 and P1 findings resolved in session. P2 items deferred to implementation sprint.**

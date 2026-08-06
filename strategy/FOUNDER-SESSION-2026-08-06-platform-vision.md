# Founder Strategy Session — Platform Vision & Build Priority
**Date:** 2026-08-06  
**Participants:** Yogesh Khandge (Founder, INST-001) + GitHub Copilot (Strategic Advisor)  
**Session Type:** Platform Architecture Brainstorm — greenfield phase, hen-vs-egg problem  
**Handover:** Enterprise Architecture (INST-004) for grooming  

---

## 1. Starting Point: The Hen-vs-Egg Problem

WAOOAW is in a `build + define + validate + identify + build` cycle. The core tension:

> *Do we build agents first (to prove value) or platform infrastructure first (to make agents real)?*

**Resolution reached:** Platform-first. Agents emerge from skill composition. Build the platform correctly once — agents are configuration, not engineering sprints.

The building layers analogy that guided the session:
- **Pillars** — core platform components (constitutional governance, execution, trust, billing)
- **Slab** — connects pillars into a solid, uniform floor
- **Rooms** — fit-for-purpose agents built on the slab
- **Furniture** — skills, tools, and content that make agents actually useful
- **Use the facilities** — customers hiring agents and getting measurable business outcomes

---

## 2. Platform Component Landscape — Disruption Opportunity Map

### Layer 0 — Constitutional Governance *(WAOOAW's unique moat)*

| Component | Status | Disruption |
|---|---|---|
| Constitutional Engine (CE) | ✅ Built | Only platform where agent behaviour is enforced by a gRPC authority, not a prompt |
| Evidence First Enforcer | ✅ Built | No claim accepted without evidence — tamper-evident audit trail from day one |
| Emergency Stop (Temporal signal) | ✅ Built | True stop, not UI state — cancels in-flight Temporal sagas |
| Decision Consequence Map (DCM) | ✅ Specified, CE extension pending | First platform to route by consequence of error, not complexity |
| **Constitutional Audit Trail Sink** | 🔲 **Not built** | Every tool call, every decision, timestamped and immutable — GDPR/DPDPA compliance as a sales feature |

### Layer 1 — Execution Infrastructure *(The deterministic engine room)*

| Component | Status | Disruption |
|---|---|---|
| UDCP Track 1 + Track 2 | ✅ Built — WC-036 | Zero structural drift. AST-driven scaffold. LLM fills logic only. |
| PTR Validation Gate | ✅ Built — WC-036 | Closed-world symbol index — hallucinated imports rejected before file write |
| Professional Runtime (PAAS) | ✅ Built | Per-session Temporal isolation — constitutional, not best-effort |
| AI Runtime (PSE/RAG/PII) | ✅ Built | Model tier routing by task complexity + PII scrubber before every prompt |
| Multi-Stack Compile Gate | ✅ Built | C#, Python, TypeScript — compile before commit, no exceptions |

### Layer 2 — Trust & Integration *(15% built — the single structural gap)*

| Component | Status | Disruption |
|---|---|---|
| **Provider Registry** | 🔲 Not built | Declarative config — any OAuth2, API key, internal JWT. New provider = new config row, not a new sprint. |
| **oauth-vault (Azure KV wrapper)** | 🔲 Not built | JIT token retrieval — credentials injected at socket boundary, never in LLM prompt history |
| **Constitutional Tool Gateway** | 🔲 Not built | MCP SDK + CE ValidateAction + Exception Translator. Non-bypassable entry point for every external call. |
| **Token Refresh Broker** | 🔲 Not built | Temporal cron workflow — generic, reads ProviderConfig. Token health is a platform guarantee. |
| Daily Token Refresh | 📋 Specified (ADR-025) | TokenDegraded → WhatsApp magic link → customer re-authorizes — no portal dependency |

### Layer 3 — Business Model Engine *(75% complete)*

| Component | Status |
|---|---|
| Billing Engine S1–S6 (Wallet, Markup, Metering, Procurement, Reconciliation) | ✅ Done |
| Trial + Promotions Engine | ✅ Done |
| **WBE-S7: Single Onboarding Payment + Renewal Saga** | 🔲 Not built |
| **WBE-S8: Full CCT Suite + Coverage Gate** | 🔲 Not built |

### Layer 4 — Skill Architecture *(0% — new component identified this session)*

| Component | What It Is |
|---|---|
| **Skill Definition Standard** | A skill is a named, versioned, testable capability unit: tools, providers, Intent Crystallizer prompt, default autonomy level, CCTs |
| **Skill Registry** | Platform catalog — `content_publish@1.2`, `ad_campaign_manager@1.0`. Adding a skill to an agent = registry lookup, not a code change. |
| **Skill-to-Agent Assignment** | Skills declared in Employment Contract. Adding = contract amendment. No redeploy. |
| **Skill Versioning** | Agents pin skill versions. Platform maintains backward compatibility. Upgrade triggers consent flow. |
| **Intent Crystallizer (generic)** | Platform pattern for structured intent approval. Each skill configures its own crystallizer prompt at registration. |

### Layer 5 — Customer & Founder Interface *(10% complete)*

| Component | Status |
|---|---|
| Landing page (`WAOOAWHome.html`) | ✅ Exists |
| Full Web Portal (auth, roles, registration, per-agent pages) | 🔲 WC-034 blocked |
| Autonomy Dial (customer-facing DCM) | 🔲 Not built |
| Agent Performance Report | 🔲 Not built |
| WhatsApp Identity Bridge (India-first) | 📋 Specified (ADR-023), not built |

---

## 3. Agent Hiring Problem Landscape (16 identified)

| # | Problem | WAOOAW Disruption Angle |
|---|---|---|
| 1 | Capability Verification Gap | Verified capability manifests with CCT-proven acceptance scenarios |
| 2 | Credential Trust Collapse | Zero-Trust Secret Engine — token never in prompt history |
| 3 | Blank-Cheque Cost Model | Wallet + budget ceiling enforcement (WBE — done) |
| 4 | Invisible Decision Trail | Constitutional Audit Trail Sink — every action evidenced |
| 5 | Skill Rot | Declarative Skill Config with versioned capability contracts |
| 6 | Scope Creep / Boundary Blur | Authorization scope locked at hire-time per C-041 |
| 7 | No Emergency Stop That Works | ADR-018 Temporal signal — saga cancellation, not UI toggle |
| 8 | Benchmark Theatre | UDCP compile gate + CCT suite as mandatory pre-hire acceptance test |
| 9 | Handoff Void | TIS/TMD schema as structured contract between agents |
| 10 | Grievance Dead-End | Employment Contract with constitutional liability chain |
| 11 | Context Amnesia | RAG + PTR as persistent working memory |
| 12 | Hiring Complexity Tax | Declarative Skill Wizard — select, configure, deploy, no code |
| 13 | No "job title" abstraction | Skill bundles under human role names — hire a "DMA Manager", not a skill set |
| 14 | Binary autonomy — no dial | Autonomy Dial per agent per action type — maps to DCM (ADR-040) |
| 15 | No performance report | Auto-generated weekly from audit sink — evidence-backed, not LLM-summarised |
| 16 | Agent versioning broken promise | Constitutional upgrade consent — customer accepts/rejects/pins |

---

## 4. Trust Layer Architecture — Finalized Decisions

### Build Strategy: Wrap & Disrupt

| Sub-layer | Approach | Rationale |
|---|---|---|
| Secret storage | **USE** Azure Key Vault (already live — `waooaw-dev-kv`) | Commodity. WAOOAW adds no value building encryption-at-rest. |
| oauth-vault service | **BUILD** thin Python service | Injection-at-boundary pattern is WAOOAW IP. Agent prompt history never contains a token. |
| MCP protocol | **ADOPT** Anthropic MCP open standard | Open, growing ecosystem. Proprietary protocol = customer lock-in, maintenance burden. |
| Constitutional Tool Gateway | **BUILD** as CE-aware wrapper over MCP SDK | CE ValidateAction + credential injection + exception translation + audit record. |
| Token refresh | **BUILD** Temporal + httpx activities | Drop Nango. Temporal in stack. Tokens never leave WAOOAW's constitutional boundary. |

### Security Decisions Locked

1. **No `{{TOKEN}}` placeholders in prompts.** Agent emits pure domain intent. Token injected at socket boundary after LLM reasoning is complete.
2. **Exception Translator, not Scrubber.** Raw exceptions never propagate to LLM. MCPToolError schema is the only output from the gateway.
3. **Audit record logs `credential_provider` and `vault_alias` only.** Full Azure KV path never written to any log.
4. **TokenDegraded → WhatsApp magic link** for re-authorization, no WC-034 portal dependency.

### Execution Pipeline

```
LLM emits pure intent: mcp.call("meta_pause_campaign", campaign_id="123")
        │
        ▼
Constitutional Tool Gateway
  → CE.ValidateAction(tenant_id, tool_name, budget_claim)
  → CE returns APPROVED(decision_id="DEC-9912")
  → oauth-vault: fetch ephemeral Bearer for (customer_id, "meta")
  → inject Authorization header at socket boundary
  → execute HTTP call to Meta Graph API
  → exception translator catches raw error — no token in output
        │
        ▼
Evidence Audit Sink
  { decision_id, agent_id, tool_name, args_hash, credential_provider,
    vault_alias, execution_status, timestamp_utc }
        │
        ▼
Sanitized result → LLM context: "Campaign 123 successfully paused."
```

---

## 5. Agent Lifecycle & DPDPA Resolution

### State Machine

| State | HR Analogy | Platform Behaviour |
|---|---|---|
| **Hired** | Offer letter signed | Employment Contract created; capabilities locked; wallet initialized |
| **Trial** | Probation | Strict trial caps; high-consequence actions require human sign-off |
| **Active** | Full employment | Automated tool execution within scope; metered wallet running |
| **Suspended** | Garden leave | CE blocks all tool calls; wallet frozen; context preserved |
| **Terminated** | Contract ended | Temporal sagas cancelled; credentials purged from Azure KV; billing closed |
| **Purged** | Offboarding complete | DPDPA erasure job runs on Operational Payload Store |

### DPDPA Collision Resolution — Proof / Payload Decoupling

```
IMMUTABLE AUDIT SINK (Proof)        OPERATIONAL PAYLOAD STORE (Data)
─────────────────────────────────   ──────────────────────────────────
Zero PII / Zero content             Raw payloads, PII, text, binaries
Cryptographic hash only             Tagged by tenant_id + agent_instance_id
WORM storage — never deleted        Erasable on Right-to-Erasure request
Proves action occurred + authority  Stores what the action touched
```

Right-to-Erasure event:
1. Operational Store wipes all data for `agent_instance_id`
2. Audit Sink retains proof record with hash and erasure timestamp
3. Platform statement: *"Agent X executed under C-041 at T. Payload hash was 0x8f... Content purged per DPDPA Order #E-102."*

**GDPR/DPDPA compliance becomes a selling point, not a liability.**

---

## 6. Constitutional Identity Delegation — The Core Platform Vision

> Agents do not call Meta API as WAOOAW API clients.  
> Agents call Meta API **as the customer** — operating within the customer's constitutional authority by delegation.

The Employment Contract is the authority delegation instrument. When signed:
- Customer grants agent authority over declared platforms within declared scope
- OAuth tokens in Azure KV are the customer's constitutional authority grants
- From Meta's perspective: Yogesh Khandge's account created the campaign
- From WAOOAW's perspective: DMA agent acted within its employment scope

**Why this matters competitively:**
- Meta builds Meta-specific agents. Google builds Google-specific agents.
- They are competing companies — no Meta agent will also be the customer's LinkedIn + YouTube + WhatsApp agent.
- WAOOAW is the only platform architecturally positioned to be the customer's **single constitutional delegate across all external platforms simultaneously**.

---

## 7. DMA as Platform Proof (Not DMA-Specific Work)

DMA is not a product feature. It is the platform running for the first time with a real purpose.

DMA has 10+ skills (content creation is one of them). This is why:
- DMA agent = skill composition, not monolithic service
- `content_publish@1.2` is a skill installed on DMA, not DMA's core
- Adding skill #11 = Skill Registry entry, not a new sprint

The DMA agent exercises every platform capability:
✅ Multi-platform constitutional identity delegation (5 OAuth providers)  
✅ Intent Crystallizer (Theme Creator → approved Campaign Brief → locked artifact)  
✅ DCM gate (publishing is DETERMINISTIC_REQUIRED — irreversible)  
✅ Autonomy Dial (different thresholds per action type)  
✅ Constitutional Tool Gateway (5 different API surfaces)  
✅ Performance Loop (post → wait → metrics → update Campaign Brief)  
✅ Billing per action with ceiling  
✅ Agent Performance Report (weekly, evidence-backed)  
✅ Employment Contract amendment (add new platform authority)  
✅ Constitutional Audit Trail (every post has a DEC reference)  

If DMA works, the platform is proven.

---

## 8. Conclusive Actionable — Handover to Enterprise Architecture (INST-004)

### A. Platform Component Status Summary

| Layer | Completion | Critical Gap |
|---|---|---|
| L0 Constitutional Governance | ~90% | Audit Trail Sink + DCM CE runtime |
| L1 Execution Infrastructure | ~95% | DCM CE proto extension |
| L2 Trust & Integration | ~15% | **Provider Registry + oauth-vault + Tool Gateway + Token Refresh — entire layer** |
| L3 Business Model | ~75% | WBE-S7 (Onboarding Payment) + WBE-S8 (CCT Gate) |
| L4 Skill Architecture | 0% | **Entire layer — new component identified this session** |
| L5 Customer Interface | ~10% | Portal + Autonomy Dial + Performance Report |

### B. Priority Build Sequence (EA to validate and groom into WCs)

**Priority 1 — Seal the Constitutional Foundation (2 sprints)**
- [ ] Constitutional Audit Trail Sink — Postgres + WORM semantic; evidence record schema defined above
- [ ] Agent Lifecycle State Machine — 6 states; owned by Business Platform; broadcast on transitions
- [ ] WBE-S7 — Single Onboarding Payment + Progressive Renewal Failure Saga (Temporal)

**Priority 2 — Trust Layer as Open Platform (4 sprints)**
- [ ] Provider Registry — declarative YAML/JSON config; Meta as row 1; supports OAuth2, API key, internal JWT
- [ ] oauth-vault — Python FastAPI daemon; Azure KV via `azure-identity`; JIT retrieval; `src/trust-layer/oauth_vault/`
- [ ] Constitutional Tool Gateway — MCP SDK wrapper + CE interceptor + exception translator; `src/trust-layer/mcp_gateway/`
- [ ] Token Refresh Broker — Temporal cron workflow; generic + Meta first; `src/trust-layer/token_refresh/`

**Priority 3 — Skill Architecture (3 sprints)**
- [ ] Skill Definition Standard — schema for skill spec (tools, providers, crystallizer prompt, CCTs, version)
- [ ] Skill Registry — platform catalog; CRUD API; version management
- [ ] Skill-to-Agent Assignment — Employment Contract `skills[]` section; amendment flow for adding/removing
- [ ] Intent Crystallizer (generic) — platform-level pattern; each skill configures its own prompt at registration
- [ ] ADR required — Provider Registry + Skill Architecture are unspecced; EA must produce ADR-042 / ADR-043 before any sprint

**Priority 4 — Product Surface (3 sprints, parallel with Priority 3)**
- [ ] Autonomy Dial — customer-facing DCM: per-agent, per-action-type threshold config
- [ ] Minimal Web Portal — auth (Keycloak) + hire agent + assign skills + view status; unblocks WC-034 partial scope
- [ ] Agent Performance Report — auto-generated weekly from Audit Sink; no LLM; evidence-backed

### C. New ADRs Required (EA action items)

| ADR | Topic | Reason |
|---|---|---|
| ADR-042 | Provider Registry Architecture | No existing ADR covers per-tenant, per-provider, runtime-configurable credential routing |
| ADR-043 | Skill Architecture Standard | No existing ADR covers skill definition, registry, versioning, or skill-to-agent assignment |
| ADR-044 | Constitutional Audit Trail Sink | ADR-009 (OTel) covers observability but not constitutional evidence persistence — separate concern |

### D. Architectural Decisions Locked (no further debate needed)

1. **Wrap & Disrupt** — Azure KV for storage, MCP SDK for transport, WAOOAW builds the constitutional wrapper only
2. **No Infisical, no Nango** — zero new vendor dependencies; Azure KV already live; Temporal already in stack
3. **Exception Translator over Scrubber** — raw exceptions never propagate; MCPToolError schema is the only gateway output
4. **Proof / Payload Decoupling** — Audit Sink = immutable proof; Operational Store = erasable data; DPDPA resolved
5. **Provider Registry is generic from day one** — Meta is first config entry, not hardcoded integration
6. **Skill Architecture** — agents are skill compositions; DMA has 10+ skills; skills are registry entries, not code changes
7. **Constitutional Identity Delegation** — agents act as customer on external platforms, not as WAOOAW API clients

### E. Deferred (Not in scope until Priority 1–3 complete)

- DMA agent-specific skill implementation (content creation, publishing, ad management etc.)
- Agriculture agent, Share Trader agent
- Mobile application
- Agency/reseller billing models (GOAL-AGENCY)
- WBE-S8 full CCT suite
- Full web portal (WC-034 complete scope)

---

*Document prepared for handover to Enterprise Architecture (INST-004) for ADR production, service boundary specification, and Work Contract grooming.*  
*Next session: EA office reviews Priority 1–3, produces ADR-042/043/044, and assigns WC numbers.*

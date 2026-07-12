# Capability to Container Map

**Produced by:** Enterprise Architect (Sprint 003)
**Date:** 2026-07-07

Each of the 26 business capabilities is owned by exactly one container. Ownership means: the container is the primary implementer and holds the authoritative state for that capability.

---

| Capability | Owning Container | Supporting Containers |
|---|---|---|
| **1.1 Evaluate Professional Candidates** | Business Platform | — |
| **1.2 Configure Employment Terms** | Business Platform | — |
| **1.3 Define Decision Space** | Business Platform | Constitutional Engine (validates boundary) |
| **1.4 Form Employment Contract** | Business Platform | Constitutional Engine (records formation event) |
| **1.5 Onboard Digital Professional** | Professional Runtime | AI Runtime (learns Creative Standard) |
| **2.1 Review Proposed Actions** | Business Platform | — |
| **2.2 Approve or Reject Actions** | Business Platform | Constitutional Engine (records approval/rejection) |
| **2.3 Confirm Scope-Boundary Crossings** | Business Platform | Constitutional Engine (records ScopeBoundaryConfirmation) |
| **2.4 Exercise Emergency Stop** | Professional Runtime | Constitutional Engine (records stop event) / Azure SignalR (transport) |
| **2.5 Monitor Professional Activity** | Business Platform | Constitutional Engine (reads ledger) |
| **2.6 Audit Evidence Ledger** | Business Platform | Constitutional Engine (read-only API) |
| **3.1 Execute Approval-Gate Work** | Professional Runtime | Constitutional Engine (Evidence First) / AI Runtime (inference) |
| **3.2 Execute Pre-Authorized Work (PAAS)** | Professional Runtime | Constitutional Engine (evidence recording) / AI Runtime (inference) |
| **3.3 Manage Creative Standard Profile** | Professional Runtime | AI Runtime (learns and applies standard) |
| **4.1 Assess Professional Performance** | Business Platform | — |
| **4.2 Expand Professional Authority** | Business Platform | Constitutional Engine (records authority grant) |
| **4.3 Restrict or Suspend Authority** | Business Platform | Constitutional Engine (records restriction) |
| **4.4 Renew Employment Contract** | Business Platform | Constitutional Engine (records renewal) |
| **5.1 Suspend Professional Employment** | Business Platform | Constitutional Engine (records suspension) |
| **5.2 Terminate Professional Employment** | Business Platform | Constitutional Engine (records termination) |
| **5.3 Export Customer Evidence** | Business Platform | Constitutional Engine (evidence export) |
| **6.1 Authenticate and Authorize Customers** | Keycloak | Business Platform (JWT validation) |
| **6.2 Isolate Tenant Data** | PostgreSQL (RLS) | All containers (JWT propagation) |
| **6.3 Record Constitutional Evidence** | Constitutional Engine | — |
| **6.4 Observe Platform Health** | All containers (OTel) | Jaeger/Azure Monitor |
| **6.5 Bill Customers** | Business Platform | — |
| **11.1 Profile Customer** | AI Runtime (Customer Profiling Pipeline) | Business Platform (profile storage via customer-profile-mcp) |
| **4.6 Earn Synthetic Approval Authority** | AI Runtime (Synthetic Approval Pipeline) | Business Platform (mode upgrade amendment), Constitutional Engine (evidence record per synthetic approval + mode upgrade event) |
| **11.2 Assess Digital Marketing Maturity** | AI Runtime (Market Research Pipeline) | Business Platform (score + heatmap storage), CE (ValidateAction before each MCP call) |
| **11.3 Execute Social Content** | Professional Runtime | AI Runtime (content creation + MCP publishing: instagram-mcp, facebook-mcp, google-business-mcp, whatsapp-business-mcp, scheduling-mcp, image-generation-mcp, video-generation-mcp), CE (evidence per action) |
| **11.4 Improve Local SEO + Reputation** | Professional Runtime | AI Runtime (seo-mcp, google-places-mcp, web-scan-mcp, google-search-console-mcp), CE (evidence) |
| **11.5 Run Paid Advertising** | Professional Runtime | AI Runtime (meta-ads-mcp, google-ads-mcp — C-043 budget check via CE.ValidateAction before every spend call), CE (budget enforcement + evidence) |
| **11.6 Optimise Conversion + Competitive Intelligence** | Professional Runtime | AI Runtime (web-optimisation-mcp, social-profile-mcp, meta-ad-library-mcp, web-search-mcp), CE (evidence) |
| **12.6 Detect and Communicate Material Signals (SIL)** | AI Runtime (Signal Watch Loop Coordinator + SignalWatchWorkflow via Temporal) | Constitutional Engine (CE.ValidateAction before proactive alert; RecordEvidence for PROACTIVE_SIGNAL_ALERT), MCP servers (weather-ensemble-mcp, agmarknet-mcp, platform-analytics-mcp, meta-ad-library-mcp), Temporal (SignalWatchWorkflow long-running per signal type per agent type) |
| **12.7 Route Customer Requests to Correct Skill(s) (SIR)** | AI Runtime (Skill Intelligence Router — LOCAL tier, ≤10ms, ₹0) | business.agent_skill_graph (pgvector intent_signatures_embedding), institutional.skill_gap_signals (gap detection), Professional Runtime (receives SIR_RoutingPlan before REASON step) |
| **11.7 Design and Execute Coherent Multi-Platform Campaigns (Campaign Theme Engine)** | AI Runtime (Campaign Theme Engine Pipeline — Components 10+11) | Constitutional Engine (CE.ValidateAction gates content_campaigns.status=ACTIVE before any content variant publish; RecordEvidence per content item), business.content_campaigns + business.campaign_weekly_themes + business.campaign_content_items + business.scr_review_records, scheduling-mcp (publish), image-generation-mcp + video-generation-mcp (content creation) |
| **11.8 Research and Recommend Platform Mix (Platform Intelligence)** | AI Runtime (Market Research Pipeline — extended) | meta-ad-library-mcp + social-profile-mcp (competitor platform research), Tier 1 RAG (platform audience demographics by domain + city), customer-profile-mcp (existing accounts), CE (evidence per recommendation) |

---

## Observations for Solution Architect

1. **Constitutional Engine is invoked by nearly every governance capability** — it is the most coupled service in the platform, by constitutional design. The Evidence First principle requires this.

2. **Professional Runtime owns all execution** — neither Business Platform nor AI Runtime executes professional work. All execution flows through Professional Runtime, which calls Constitutional Engine before returning.

3. **AI Runtime has no governance responsibilities** — it is a pure execution tool. Governance is always done by its caller (Professional Runtime + Constitutional Engine). AI Runtime never writes to the ledger.

4. **Business Platform is the customer-facing API** — it is the entry point for all customer interactions. It delegates to Constitutional Engine for governance and to Professional Runtime for execution.

5. **Emergency Stop is split across Professional Runtime (handler) and Constitutional Engine (evidence)** — the halt must happen first, the evidence must be recorded before confirmation is sent. This is the latency-critical path.

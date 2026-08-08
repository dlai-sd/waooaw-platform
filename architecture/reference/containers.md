# C4 Level 2 — Container Diagram

**Produced by:** Enterprise Architect (Sprint 003, reconciled for platform v1.44.0 under WC-049)
**Date:** 2026-07-07 (updated 2026-08-08)
**ADR References:** ADR-001 (gRPC), ADR-003 (JWT/RLS), ADR-004 (SignalR), ADR-005 (PAAS session), ADR-008 (Keycloak), ADR-009 (OTel), ADR-012 (GHCR), ADR-019 (RAG), ADR-020 (MCP), ADR-021 (oauth-vault), ADR-034 (WBE), ADR-042 (CTG + Provider Registry), ADR-043 (Skill Architecture), ADR-044 (Audit Trail Sink)

---

## Container Diagram

```
Customer Browser / Mobile App
        │
        │  HTTPS REST  +  WSS (Emergency Stop)
        │
        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  Azure Container Apps Environment  /  Docker Compose (dev)                    │
│                                                                               │
│  ┌─────────────────────────────┐                                              │
│  │  Next.js Web App            │  Port 3000                                   │
│  │  TypeScript / React         │  Serves customer PWA                         │
│  └──────────────┬──────────────┘                                              │
│                 │ REST HTTPS                                                   │
│  ┌──────────────▼──────────────┐   gRPC (mTLS cloud / plain dev)             │
│  │  Business Platform          │──────────────────────────────────────────►  │
│  │  .NET 9  Port 5001 (REST)   │   ┌──────────────────────────────────────┐  │
│  │                             │   │  Constitutional Engine  .NET 9        │  │
│  │  - Employment management    │   │  Port 5002 (gRPC, internal only)      │  │
│  │  - Approval workflows       │   │                                       │  │
│  │  - Skill Catalog (ADR-043)  │   │  - Evidence First enforcer            │  │
│  │  - Provider Registry        │   │  - audit_sink schema (WORM, ADR-044)  │  │
│  │    (ADR-042)                │◄──│  - RecordErasure RPC (ADR-044)        │  │
│  │  - payload_store schema     │   │  - Authority licensing                │  │
│  │    (erasable, ADR-044)      │   │  - Emergency Stop handler             │  │
│  └──────────────┬──────────────┘   └──────────────────┬───────────────────┘  │
│                 │ REST / WSS                           │ gRPC                 │
│  ┌──────────────▼──────────────┐◄─────────────────────┘                      │
│  │  Professional Runtime       │                                              │
│  │  Python FastAPI  Port 5003  │                                              │
│  │                             │                                              │
│  │  - Approval-gate engine     │  REST (internal)                            │
│  │  - PAAS execution engine    │─────────────────────────────────────────►   │
│  │  - Skill Runtime (ADR-043)  │   ┌──────────────────────────────────────┐  │
│  │  - CTG library (ADR-042)    │   │  AI Runtime  Python FastAPI           │  │
│  │  - Emergency Stop WSS       │   │  Port 5004 (internal only)            │  │
│  │  - Temporal worker          │   │                                       │  │
│  └──────────────┬──────────────┘   │  - PSE tier routing                   │  │
│                 │ HTTP (internal)  │  - CTG library (ADR-042) — all        │  │
│                 │                  │    external calls: LLM + OAuth API    │  │
│  ┌──────────────▼──────────────┐   │  - RAG pipeline (ADR-019)            │  │
│  │  oauth-vault                │◄──│  - PII injection guard                │  │
│  │  Python FastAPI             │   └──────────────────────────────────────┘  │
│  │  Port 8130 (internal only)  │                                              │
│  │                             │                                              │
│  │  - JIT token retrieval      │                                              │
│  │  - Token health / refresh   │                                              │
│  │  - Revocation (CE-gated)    │                                              │
│  └──────────────┬──────────────┘                                              │
│                 │ HTTPS (external)                                            │
│  ┌──────────────▼──────────────┐                                              │
│  │  WAOOAW Billing Engine      │  Python FastAPI · Port 8140 (internal)       │
│  │  - Prepaid wallet gate      │  - Payment + renewal lifecycle               │
│  │  - Metering + pricing       │  - Reconciliation halt                       │
│  └─────────────────────────────┘                                              │
│  Infrastructure │                                                             │
│  ┌──────────────▼──────────────┐  ┌──────────────────────────────────────┐  │
│  │  Azure Key Vault            │  │  PostgreSQL 16 + pgvector            │  │
│  │  waooaw-dev-kv              │  │  Port 5432                           │  │
│  │  (master key + tokens)      │  │  - constitutional / audit_sink (CE)  │  │
│  └─────────────────────────────┘  │  - business / payload_store (BP)     │  │
│                                   │  - professional / skills (BP)        │  │
│  ┌─────────────────────────────┐  │  - Row-Level Security (ADR-003)      │  │
│  │  Temporal  Port 7233        │  └──────────────────────────────────────┘  │
│  │  Self-host dev / Cloud prod │                                              │
│  └─────────────────────────────┘  ┌──────────────────────────────────────┐  │
│                                   │  Keycloak  Port 8443  (ADR-008)      │  │
│  ┌─────────────────────────────┐  └──────────────────────────────────────┘  │
│  │  Azure SignalR (cloud only) │                                              │
│  │  Emergency Stop backplane   │  ┌──────────────────────────────────────┐  │
│  └─────────────────────────────┘  │  Jaeger (dev) → Azure Monitor (cloud)│  │
│                                   │  Port 16686  (ADR-009)               │  │
│                                   └──────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘

CTG Call Flow (ADR-042):
  PR or AIR  →  CTG.call(tool, args, session_ctx)
                  │ gRPC
                  ▼
              CE.ValidateAction → ALLOW/DENY
                  │ HTTP (internal)
                  ▼
              oauth-vault → Azure Key Vault → ephemeral token (in-memory)
                  │
                  ▼
              Execute: inject token at socket boundary → external API
                  │
                  ▼
              Write evidence record → CE audit_sink schema
```

---

## Container Descriptions

### Next.js Web App
- **Technology:** Next.js 14, TypeScript, React, Tailwind CSS
- **Responsibility:** Customer-facing PWA. Hiring wizard, approval dashboard, evidence viewer, Emergency Stop button, performance dashboard
- **Communication:** REST to Business Platform; WebSocket to Professional Runtime (Emergency Stop)
- **Hosting:** Container Apps (cloud) / port 3000 (dev)

### Business Platform
- **Technology:** .NET 9, ASP.NET Core, Entity Framework Core, Temporal SDK
- **Responsibility:** External REST API for all customer operations. Employment lifecycle management, approval workflow state machine, Temporal workflow orchestration, JWT validation, multi-tenant isolation. Owns **Skill Catalog** (`skills` table, ADR-043), **Provider Registry** (`provider_configs` table, ADR-042), and **Erasable Payload Store** (`payload_store` schema, ADR-044).
- **Communication:** Calls Constitutional Engine (gRPC, synchronous, Evidence First); publishes Temporal workflows; reads/writes PostgreSQL business + payload_store schemas
- **Hosting:** Container Apps (cloud) / port 5001 (dev)

### Constitutional Engine
- **Technology:** .NET 9, gRPC (Grpc.AspNetCore), Entity Framework Core
- **Responsibility:** Evidence First enforcer. Owns the **Constitutional Audit Trail Sink** (`audit_sink` schema — INSERT-only, no UPDATE/DELETE, ADR-044). Handles `RecordErasure` RPC for DPDPA compliance. Authority license management, PAAS Decision Space validation, Emergency Stop processing. Internal-only — never exposed externally.
- **Communication:** gRPC server (Business Platform, Professional Runtime, and CTG library are clients); reads/writes PostgreSQL constitutional + audit_sink schemas
- **Hosting:** Container Apps (cloud, internal ingress only) / port 5002 (dev, Docker bridge only)

### Professional Runtime
- **Technology:** Python 3.12, FastAPI, Temporal SDK (Python)
- **Responsibility:** Three execution engines in one service: (1) Approval-Gate Engine — manages proposal/approval/execution state machine; (2) PAAS Engine — session-affinity per customer (ADR-005); (3) **Skill Runtime** (in-process, ADR-043) — resolves skill manifests from BP Skill Catalog at session open, enforces `authorized_tools`, runs Intent Crystallizer for skills that require it. CTG library imported here for all external tool calls — every call governed by CE.ValidateAction.
- **Communication:** gRPC client to CE; REST client to AIR; HTTP client to BP (Skill Catalog, Provider Registry); HTTP client to oauth-vault (via CTG); WebSocket server for Emergency Stop; Temporal worker
- **Hosting:** Container Apps (cloud, session-affinity enabled) / port 5003 (dev)

### AI Runtime
- **Technology:** Python 3.12, FastAPI, LLM client libraries
- **Responsibility:** LLM gateway — abstracts all AI provider communication. **After WC-039:** all LLM provider calls route through the **CTG library** (ADR-042) — no direct SDK calls remain. CTG → CE.ValidateAction → oauth-vault → LLM API. Every LLM call produces a constitutional evidence record (budget enforcement, C-043). Tool execution via MCP clients (ADR-020). RAG pipeline (ADR-019). PII injection guard. Internal-only.
- **Communication:** Called by Professional Runtime (REST internal); CTG library calls CE (gRPC) + oauth-vault (HTTP) + LLM provider (HTTPS); calls vector store in PostgreSQL (pgvector)
- **Hosting:** Container Apps (cloud, internal ingress only) / port 5004 (dev)
- **Breaking change (ADR-042):** WC-039 refactors direct LLM SDK calls to CTG — no code touches LLM provider SDK directly after WC-039.

### PostgreSQL 16 + pgvector
- **Technology:** PostgreSQL 16 with pgvector extension
- **Responsibility:** All persistent state. Schema zones (updated 2026-08-06):
  - `constitutional` — CE: evidence records, authority licenses (append-only)
  - `audit_sink` — CE: WORM evidence records (INSERT-only, ADR-044); retains proof forever
  - `business` — BP: employment contracts, organizations (standard CRUD)
  - `payload_store` — BP: operational payloads (erasable on DPDPA request, ADR-044)
  - `skills` — BP: skill catalog (ADR-043)
  - `provider_configs` — BP: provider registry (ADR-042)
  - `professional` — PR: professional identities, experience ledger
  - `vectors` — shared pgvector store (RAG, ADR-019)
  Row-Level Security enforces multi-tenant isolation across all schemas.
- **Hosting:** Azure PostgreSQL Flexible Server (cloud) / Docker container (dev)

### Keycloak
- **Technology:** Keycloak 25.x (pinned, ADR-008)
- **Responsibility:** OAuth broker. Federates Google (and future providers) into a single Keycloak JWT. Application services never talk directly to OAuth providers.
- **Hosting:** Container Apps (cloud) / Docker container (dev)

### oauth-vault *(new — WC-038)*
- **Technology:** Python 3.12, FastAPI, `azure-identity` (DefaultAzureCredential)
- **Responsibility:** Dedicated token storage and JIT retrieval service. Stores customer OAuth tokens and platform API keys in Azure Key Vault (`waooaw-dev-kv`). Returns ephemeral tokens to CTG callers — token is held in-memory in CTG, injected at socket boundary, never logged. Runs background refresh scheduler (asyncio) for proactive token renewal. On refresh failure: publishes `PLATFORM_TOKEN_EXPIRED` event to Professional Runtime. Revocation requires a CE evidence record before AKV delete. Internal-only — not exposed externally.
- **Communication:** Called by CTG library (HTTP, JIT token retrieval); called by BP (OAuth connect/revoke); calls Azure Key Vault (HTTPS external); calls CE (gRPC, revocation evidence)
- **Hosting:** Container Apps (cloud, internal ingress only) / port 8130 (dev, Docker bridge only)
- **Security invariant (ADR-042):** Full AKV URL (`https://...vault.azure.net/...`) never written to any log. Only `vault_alias` logged.

### WAOOAW Billing Engine *(WC-025→033, WC-042→043)*
- **Technology:** Python 3.12, FastAPI, PostgreSQL, Redis
- **Responsibility:** Agent-agnostic prepaid wallet buckets, pricing and margin floors, usage metering, platform procurement, Razorpay onboarding/payment lifecycle, renewal failure handling, and reconciliation self-halt.
- **Communication:** Called by BP for subscription/payment operations and intended to be called by AIR before LLM dispatch; AIR end-to-end reserve integration remains only partially evidenced.
- **Hosting:** Internal service on port 8140. Repository implementation and tests exist; environment deployment and customer-operation evidence are unverified.

### Temporal
- **Technology:** Self-hosted Temporal 1.24 (dev/QA) / Temporal Cloud (UAT/prod) — ADR-015
- **Responsibility:** Durable workflow orchestration for employment lifecycle events (hiring, renewal, suspension, termination)
- **Hosting:** Docker container sharing PostgreSQL (dev) / Temporal Cloud (prod)

### Azure SignalR
- **Technology:** Azure SignalR Service (cloud) / plain WebSocket (dev) — ADR-004
- **Responsibility:** Emergency Stop WebSocket backplane. Routes Emergency Stop commands to the correct Professional Runtime replica regardless of horizontal scaling.
- **Hosting:** Azure managed service (cloud only)

---

## MCP Integration Layer (v0.11.0 — ADR-020)

The AI Runtime is an MCP client. Agent-specific capabilities that require real-time external data are delivered through MCP-compliant servers. Each MCP server is a lightweight sidecar container — it does NOT contain business logic; it contains data access adapters only.

**Constitutional constraint (C-041):** Every MCP tool call is gated by a `CE.ValidateAction` call before execution. This is enforced in the AI Runtime's MCP client, not in the MCP servers themselves.

### MCP Server Inventory

| MCP Server | Used By | Data Source | Deployment |
|---|---|---|---|
| `weather-ensemble-mcp` | Agricultural Advisory Agent | IMD API, OpenWeatherMap, ECMWF, Weather.gov, AccuWeather (5-source ensemble) | Sidecar container (dev), Container Apps (cloud) |
| `agmarknet-mcp` | Agricultural Advisory Agent | Agmarknet government portal, eNAM | Sidecar container (dev), Container Apps (cloud) |
| `whatsapp-voice-mcp` | Agricultural Advisory Agent | WhatsApp Business Cloud API (voice messages) | Sidecar container (dev), Container Apps (cloud) |
| `broker-api-mcp` | Trading Agent | Zerodha Kite, ICICI Direct, Angel One (configurable at employment contract time) | Sidecar container (dev), Container Apps (cloud) |
| `whatsapp-business-mcp` | Digital Marketing Agent | WhatsApp Business API | Sidecar container (dev), Container Apps (cloud) |
| `scheduling-mcp` | Digital Marketing Agent | Internal scheduling store (PostgreSQL) | Sidecar container (dev), Container Apps (cloud) |
| `instagram-mcp` | Digital Marketing Agent | Meta Graph API (Instagram) | Sidecar container (dev), Container Apps (cloud) |
| `facebook-mcp` | Digital Marketing Agent | Meta Graph API (Facebook Pages) | Sidecar container (dev), Container Apps (cloud) |
| `google-business-mcp` | Digital Marketing Agent | Google Business Profile API | Sidecar container (dev), Container Apps (cloud) |
| `platform-analytics-mcp` | Digital Marketing Agent | Meta Insights API, Google Analytics 4, GBP Insights (read-only) | Sidecar container (dev), Container Apps (cloud) |
| `image-generation-mcp` | Digital Marketing Agent | OpenAI DALL-E / Azure AI Image Generation | Sidecar container (dev), Container Apps (cloud) |
| `video-generation-mcp` | Digital Marketing Agent | Azure AI Video Generation / RunwayML (configurable) | Sidecar container (dev), Container Apps (cloud) |
| `customer-profile-mcp` | Digital Marketing Agent (v2.0) | PostgreSQL — digital_marketing_profiles, digital_marketing_maturity_scores | Sidecar container (dev), Container Apps (cloud) |
| `web-search-mcp` | Digital Marketing Agent (v2.0) | Public web search API (Brave Search / Bing Search — no auth required) | Sidecar container (dev), Container Apps (cloud) |
| `google-places-mcp` | Digital Marketing Agent (v2.0) | Google Places API (public business data) | Sidecar container (dev), Container Apps (cloud) |
| `social-profile-mcp` | Digital Marketing Agent (v2.0) | Public social profile data via web search and public page scraping — no platform API authentication; uses web-search-mcp pattern internally for social profile discovery (C-041: authenticated Graph API calls prohibited for this server) | Sidecar container (dev), Container Apps (cloud) |
| `meta-ad-library-mcp` | Digital Marketing Agent (v2.0) | Meta Ad Library API (public — no auth required) | Sidecar container (dev), Container Apps (cloud) |
| `web-scan-mcp` | Digital Marketing Agent (v2.0) | HTTP page scanning (no auth — public pages only; C-043: authenticated access prohibited) | Sidecar container (dev), Container Apps (cloud) |
| `seo-mcp` | Digital Marketing Agent (v2.0) | SEO analysis APIs (keyword data, ranking signals) | Sidecar container (dev), Container Apps (cloud) |
| `google-search-console-mcp` | Digital Marketing Agent (v2.0) | Google Search Console API (customer OAuth — customer-private read-only) | Sidecar container (dev), Container Apps (cloud) |
| `meta-ads-mcp` | Digital Marketing Agent (v2.0) | Meta Marketing API (customer ad account — C-043 budget cap enforced pre-call) | Sidecar container (dev), Container Apps (cloud) |
| `google-ads-mcp` | Digital Marketing Agent (v2.0) | Google Ads API (customer ad account — C-043 budget cap enforced pre-call) | Sidecar container (dev), Container Apps (cloud) |
| `web-optimisation-mcp` | Digital Marketing Agent (v2.0) | CRO/A-B testing platform API (e.g., VWO, Google Optimize successor) | Sidecar container (dev), Container Apps (cloud) |
| `youtube-mcp` | Digital Marketing Agent (v2.5) | YouTube Data API v3 (customer OAuth — upload, metadata, analytics) | **PLANNED** — Founder action: enable YouTube Data API in existing Google Cloud project. Sidecar container (dev), Container Apps (cloud) |
| `linkedin-mcp` | Digital Marketing Agent (v2.5) | LinkedIn Marketing API (company page posts, analytics) | **PLANNED** — Founder action: WAOOAW LinkedIn Company Page + LinkedIn Partner Program application required. Lead time: 2-4 weeks. |
| `x-mcp` | Digital Marketing Agent (v2.5) | X (Twitter) API v2 (post creation, analytics) | **PLANNED — PENDING FOUNDER DECISION** — X API Basic tier: $100/month for write access. Defer until Founder approves cost. |
| `pinterest-mcp` | Digital Marketing Agent (v2.5) | Pinterest API v5 (Pin creation, analytics) | **PLANNED** — Founder action: Pinterest Developer Account registration. Free. 2-3 days. |
| `threads-mcp` | Digital Marketing Agent (v2.5) | Meta Threads API (post creation) | **PLANNED** — Requires same Meta Business Manager as instagram-mcp. Available after Meta BM verification. |
| `oauth-vault` | All agents requiring customer OAuth delegation | Secure token storage + refresh scheduler for Meta, Google OAuth tokens (ADR-021) | Sidecar container (dev), Container Apps (cloud) |
| `razorpay-mcp` | Business Platform (billing) | Razorpay Subscriptions + Payments API (ADR-022) | Sidecar container (dev), Container Apps (cloud) |
| `pdf-generation-mcp` | Business Platform + AI Runtime (Maturity Report) | HTML-to-PDF generation (Gotenberg/Puppeteer) for reports and invoices | Sidecar container (dev), Container Apps (cloud) |
| `email-mcp` | AI Runtime (performance narrative delivery) | Transactional email — SendGrid/SES for Maturity Reports, billing invoices | Sidecar container (dev), Container Apps (cloud) |
| `push-notification-mcp` | Business Platform (approval notifications, skill alerts) | Firebase FCM / APNs push notifications for approval requests and skill alerts | Sidecar container (dev), Container Apps (cloud) |
| `platform-operations-mcp` | Platform Operations Agent (L1/L2/L3) | Platform health data aggregation, Temporal API, incident management (C-046) | Sidecar container (dev), Container Apps (cloud) |
| `waooaw-ads-manager` | Skill 11 Paid Advertising (DMA) | WAOOAW Master Meta Business Manager (MBM) + Google Ads MCC sub-account management; page access requests; daily billing reconciliation (ADR-026, C-056) | Internal service — port 8143, NEVER externally exposed. Uses WAOOAW_META_SYSTEM_USER_ACCESS_TOKEN + WAOOAW_GOOGLE_ADS_MCC_DEVELOPER_TOKEN (Azure Key Vault — ADR-014, NOT oauth-vault). **PLANNED — Founder action: Meta Business Partner status + Google MCC setup required.** |
| `cms-mcp` | Skill 10 Local SEO (DMA) — Blog publishing | WordPress REST API (primary); Squarespace Content API (secondary). Publishes approved blog posts, injects schema markup. Detects CMS type from web-scan-mcp output. | Port 8144. Sidecar container (dev). Requires customer's CMS API key in oauth-vault. **DEGRADABLE** — if customer has no CMS integration, delivers blog post as formatted document for manual paste. |
| `image-to-video-mcp` | Skill 8 Video (DMA) — Track 1 Photo-to-Video | Kling AI 2.0 API — animates customer photos into cinematic video. 5-second clips from single image with realistic motion and face rendering. Best quality for photography-based animation. | Port 8145. Uses KLING_AI_API_KEY (Azure Key Vault). **Founder action: Kling AI API key required.** |
| `avatar-generation-mcp` | Skill 8 Video (DMA) — Track 2 Digital Twin | HeyGen 2.0 API — creates talking-head avatar from 3-minute source video. Hindi/Marathi lip-sync support. Generates avatar video from script + voice clone. | Port 8146. Uses HEYGEN_API_KEY (Azure Key Vault). **Founder action: HeyGen API key required.** |
| `voice-clone-mcp` | Skill 8 Video (DMA) — Track 2 Digital Twin | ElevenLabs Turbo v2 API — voice cloning from 30 seconds of audio. Best Indian accent support. Real-time voice synthesis for avatar video delivery. | Port 8147. Uses ELEVENLABS_API_KEY (Azure Key Vault). **Founder action: ElevenLabs API key required.** |
| `text-to-video-mcp` | Skill 8 Video (DMA) — Track 3 Generative | Runway ML Gen-3 Alpha API — text-prompt to video generation. Most controllable output for brand-consistent promotional content. Camera movement control for professional aesthetic. | Port 8148. Uses RUNWAYML_API_KEY (Azure Key Vault). **Founder action: Runway ML API key required.** |
| `prompt-registry-mcp` | AI Runtime (AD-018 Prompt Governance) | Serves active prompt versions from `institutional.agent_prompt_versions`; invalidates cache on version change | Sidecar container (dev, lightweight), Container Apps (cloud) |
| `market-data-mcp` | Trading Agent (Skills 1, 3, 4) | NSE/BSE live price feed, OHLCV candles, options chain, OI/Greeks, India VIX, crypto prices (CoinDCX/WazirX) | Sidecar container (dev), Container Apps (cloud) |
| `crypto-exchange-mcp` | Trading Agent (Skill 4) | Crypto spot + DCA execution on CoinDCX / WazirX (India compliant exchanges) | Sidecar container (dev), Container Apps (cloud) |
| `nse-calendar-mcp` | Trading Agent (all skills) | NSE/BSE market holidays, circuit filter status, exchange halts | Sidecar container (dev), Container Apps (cloud) |
| `enam-mcp` | Agricultural Advisor Agent (Skill 3) | eNAM (National Agriculture Market) portal price data | Sidecar container (dev), Container Apps (cloud) |
| `government-scheme-mcp` | Agricultural Advisor Agent (Skills 3, 4, 5) | PMFBY status, MSP announcements, APMC rules, government scheme updates (India) | Sidecar container (dev), Container Apps (cloud) |
| `phone-identity-service` | All C-042 agents via Business Platform webhook handler | WhatsApp phone-to-organisation_id mapping; auto-registration; session token issuance; HMAC webhook validation (ADR-023) | Internal platform service (dev), Container Apps (cloud) |

### MCP Architecture Principles (ADR-020)

- MCP servers are stateless adapters — all state is in PostgreSQL
- MCP servers run in the same Azure Container Apps Environment as the AI Runtime (no external network for internal calls)
- Each MCP server exposes only the tools listed in its Tool Catalogue (GENESIS Part 05, Section 5)
- CE.ValidateAction is called by the AI Runtime before the MCP call — MCP servers do not validate authority
- Tool call results are returned to the AI Runtime for Vocabulary Translation Layer processing before reaching the customer
- Production MCP servers require mTLS to the AI Runtime (same trust domain as CE — ADR-007)

---

## Communication Protocol Summary

| From | To | Protocol | Sync/Async | Why |
|---|---|---|---|---|
| Next.js | Business Platform | REST HTTPS | Sync | External customer API |
| Next.js | Professional Runtime | WebSocket | Persistent | Emergency Stop (AD-001) |
| Business Platform | Constitutional Engine | gRPC | Sync | Evidence First (AD-002) |
| Professional Runtime | Constitutional Engine | gRPC | Sync | Evidence First (AD-002) |
| Professional Runtime | AI Runtime | REST (internal) | Sync | Decision Space constrained inference |
| AI Runtime | MCP servers | MCP (HTTP, internal) | Sync | Tool execution (C-041 gated) |
| Business Platform | Temporal | Temporal SDK | Async | Durable workflow orchestration |
| Professional Runtime | Temporal | Temporal SDK (worker) | Async | Workflow execution |
| All services | PostgreSQL | TCP (EF Core / asyncpg) | Sync | Persistence |

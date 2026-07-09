# C4 Level 2 — Container Diagram

**Produced by:** Enterprise Architect (Sprint 003, updated v0.11.0)
**Date:** 2026-07-07 (updated 2026-07-08)
**ADR References:** ADR-001 (gRPC), ADR-003 (JWT/RLS), ADR-004 (SignalR), ADR-005 (PAAS session), ADR-008 (Keycloak), ADR-009 (OTel), ADR-012 (GHCR), ADR-019 (RAG), ADR-020 (MCP)

---

## Container Diagram

```
Customer Browser / Mobile App
        │
        │  HTTPS REST  +  WSS (Emergency Stop)
        │
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Azure Container Apps Environment  /  Docker Compose (dev)           │
│                                                                      │
│  ┌─────────────────────────────┐                                     │
│  │  Next.js Web App            │  Port 3000                          │
│  │  TypeScript / React         │  Serves customer PWA                │
│  │  Calls Business Platform    │  → REST /api/*                      │
│  └──────────────┬──────────────┘                                     │
│                 │ REST HTTPS                                          │
│  ┌──────────────▼──────────────┐   gRPC (mTLS cloud / plain dev)    │
│  │  Business Platform          │──────────────────────────────────►  │
│  │  .NET 9 Modular Monolith    │   ┌─────────────────────────────┐  │
│  │  Port 5001 (REST)           │   │  Constitutional Engine       │  │
│  │                             │   │  .NET 9                      │  │
│  │  - Employment management    │   │  Port 5002 (gRPC internal)   │  │
│  │  - Approval workflows       │   │                              │  │
│  │  - Temporal client          │   │  - Evidence First enforcer   │  │
│  │  - Customer JWT validation  │◄──│  - Audit Ledger writes       │  │
│  └──────────────┬──────────────┘   │  - Authority licensing       │  │
│                 │ REST HTTPS       │  - PAAS boundary validation  │  │
│                 │ WSS Emergency Stop│  - Emergency Stop handler   │  │
│  ┌──────────────▼──────────────┐   └─────────────┬───────────────┘  │
│  │  Professional Runtime       │                 │                   │
│  │  Python FastAPI             │  gRPC           │                   │
│  │  Port 5003                  │◄────────────────┘                   │
│  │                             │                                     │
│  │  - Approval-gate engine     │  REST (internal)                    │
│  │  - PAAS execution engine    │──────────────────────────────────►  │
│  │  - Emergency Stop WSS       │   ┌─────────────────────────────┐  │
│  │  - Temporal worker          │   │  AI Runtime                 │  │
│  └─────────────────────────────┘   │  Python FastAPI              │  │
│                                    │  Port 5004 (internal)        │  │
│  Infrastructure                    │                              │  │
│  ┌──────────────────────────────┐  │  - LLM gateway               │  │
│  │  PostgreSQL 16 + pgvector   │  │  - Decision Space reasoning  │  │
│  │  Port 5432                  │  │  - Tool execution            │  │
│  │  - Constitutional schema    │  └─────────────────────────────┘  │
│  │  - Business schema          │                                     │
│  │  - Row-Level Security       │  ┌──────────────────────────────┐  │
│  └──────────────────────────────┘  │  Keycloak                    │  │
│                                    │  Port 8443                   │  │
│  ┌──────────────────────────────┐  │  OAuth broker (ADR-008)      │  │
│  │  Temporal                   │  └──────────────────────────────┘  │
│  │  Port 7233 (dev: self-host) │                                     │
│  │  Temporal Cloud (prod)      │  ┌──────────────────────────────┐  │
│  └──────────────────────────────┘  │  Jaeger (dev only)           │  │
│                                    │  Port 16686                  │  │
│  ┌──────────────────────────────┐  │  OTel traces → Azure Monitor │  │
│  │  Azure SignalR (cloud only) │  │  (cloud, ADR-009)            │  │
│  │  Emergency Stop backplane   │  └──────────────────────────────┘  │
│  └──────────────────────────────┘                                     │
└──────────────────────────────────────────────────────────────────────┘
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
- **Responsibility:** External REST API for all customer operations. Employment lifecycle management, approval workflow state machine, Temporal workflow orchestration, JWT validation, multi-tenant isolation
- **Communication:** Calls Constitutional Engine (gRPC, synchronous, Evidence First); publishes Temporal workflows; reads/writes PostgreSQL business schema
- **Hosting:** Container Apps (cloud) / port 5001 (dev)

### Constitutional Engine
- **Technology:** .NET 9, gRPC (Grpc.AspNetCore), Entity Framework Core
- **Responsibility:** Evidence First enforcer. The only service that writes to the Constitutional Audit Ledger. Authority license management, PAAS Decision Space validation, Emergency Stop processing. Internal-only — never exposed externally.
- **Communication:** gRPC server (Business Platform and Professional Runtime are clients); reads/writes PostgreSQL constitutional schema (append-only on audit ledger)
- **Hosting:** Container Apps (cloud, internal ingress only) / port 5002 (dev, Docker bridge only)

### Professional Runtime
- **Technology:** Python 3.12, FastAPI, Temporal SDK (Python)
- **Responsibility:** Two execution engines in one service: (1) Approval-Gate Engine — manages proposal/approval/execution state machine, calls Constitutional Engine for each governance event; (2) PAAS Engine — in-memory Decision Space validation, zero network calls in hot path, session-affinity per customer (ADR-005)
- **Communication:** gRPC client to Constitutional Engine; REST client to AI Runtime; WebSocket server for Emergency Stop; Temporal worker
- **Hosting:** Container Apps (cloud, session-affinity enabled) / port 5003 (dev)

### AI Runtime
- **Technology:** Python 3.12, FastAPI, LLM client libraries
- **Responsibility:** LLM gateway — abstracts all AI provider communication. Receives Decision Space context for every inference call, ensuring AI never operates beyond licensed scope. Tool execution via MCP clients (ADR-020). Vocabulary Translation Layer (DP-013) for C-042 agents. RAG pipeline for domain specialization (ADR-019). Internal-only.
- **Communication:** Called by Professional Runtime (REST internal); calls LLM providers (HTTPS external); calls MCP Integration Layer services; calls vector store in PostgreSQL (pgvector)
- **Hosting:** Container Apps (cloud, internal ingress only) / port 5004 (dev)

### PostgreSQL 16 + pgvector
- **Technology:** PostgreSQL 16 with pgvector extension
- **Responsibility:** All persistent state. Three schema zones: `constitutional` (audit ledger, authority licenses — append-only), `business` (employment contracts, organizations — standard CRUD), `professional` (professional identities, experience ledger). Row-Level Security enforces multi-tenant isolation.
- **Hosting:** Azure PostgreSQL Flexible Server (cloud) / Docker container (dev)

### Keycloak
- **Technology:** Keycloak 25.x (pinned, ADR-008)
- **Responsibility:** OAuth broker. Federates Google (and future providers) into a single Keycloak JWT. Application services never talk directly to OAuth providers.
- **Hosting:** Container Apps (cloud) / Docker container (dev)

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
| `oauth-vault` | All agents requiring customer OAuth delegation | Secure token storage + refresh scheduler for Meta, Google OAuth tokens (ADR-021) | Sidecar container (dev), Container Apps (cloud) |
| `razorpay-mcp` | Business Platform (billing) | Razorpay Subscriptions + Payments API (ADR-022) | Sidecar container (dev), Container Apps (cloud) |
| `pdf-generation-mcp` | Business Platform + AI Runtime (Maturity Report) | HTML-to-PDF generation (Gotenberg/Puppeteer) for reports and invoices | Sidecar container (dev), Container Apps (cloud) |
| `email-mcp` | AI Runtime (performance narrative delivery) | Transactional email — SendGrid/SES for Maturity Reports, billing invoices | Sidecar container (dev), Container Apps (cloud) |
| `push-notification-mcp` | Business Platform (approval notifications, skill alerts) | Firebase FCM / APNs push notifications for approval requests and skill alerts | Sidecar container (dev), Container Apps (cloud) |
| `platform-operations-mcp` | Platform Operations Agent (L1/L2/L3) | Platform health data aggregation, Temporal API, incident management (C-046) | Sidecar container (dev), Container Apps (cloud) |
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

# C4 Level 2 — Container Diagram

**Produced by:** Enterprise Architect (Sprint 003)
**Date:** 2026-07-07
**ADR References:** ADR-001 (gRPC), ADR-003 (JWT/RLS), ADR-004 (SignalR), ADR-005 (PAAS session), ADR-008 (Keycloak), ADR-009 (OTel), ADR-012 (GHCR)

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
- **Responsibility:** LLM gateway — abstracts all AI provider communication. Receives Decision Space context for every inference call, ensuring AI never operates beyond licensed scope. Tool execution (web search, API calls, market data queries). Internal-only.
- **Communication:** Called by Professional Runtime (REST internal); calls LLM providers (HTTPS external); calls market data APIs (trading scenario)
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

## Communication Protocol Summary

| From | To | Protocol | Sync/Async | Why |
|---|---|---|---|---|
| Next.js | Business Platform | REST HTTPS | Sync | External customer API |
| Next.js | Professional Runtime | WebSocket | Persistent | Emergency Stop (AD-001) |
| Business Platform | Constitutional Engine | gRPC | Sync | Evidence First (AD-002) |
| Professional Runtime | Constitutional Engine | gRPC | Sync | Evidence First (AD-002) |
| Professional Runtime | AI Runtime | REST (internal) | Sync | Decision Space constrained inference |
| Business Platform | Temporal | Temporal SDK | Async | Durable workflow orchestration |
| Professional Runtime | Temporal | Temporal SDK (worker) | Async | Workflow execution |
| All services | PostgreSQL | TCP (EF Core / asyncpg) | Sync | Persistence |

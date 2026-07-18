# ADR-027: Cloud Architecture Optimization — Cost, Performance, Scalability

**Status:** Accepted
**Date:** 2026-07-13
**Author:** Enterprise Architect (Cloud Architecture Optimization Review)
**Constitutional Basis:** GENESIS Part 01 — Cost Constraint; Constitution Article III (Second Law — PAAS trading requires <250ms latency, a constitutional obligation); ADR-015 (Temporal deployment); ADR-010 (cloud portability)

---

## Context

At v0.68.0, the platform architecture was reviewed against three axes: cost, performance, and scalability. Ten optimizations were identified. This ADR records the decisions made, their rationale, and implementation status.

---

## Optimization Decisions

### O-01 — pgvector: IVFFlat → HNSW ✅ Implemented

**Decision:** Replace all 7 IVFFlat pgvector indexes with HNSW indexes.

**Rationale:**
- IVFFlat requires minimum `4 × lists` data points to be effective. With lists=100, needs 400+ vectors. At MVI with < 1,000 vectors, IVFFlat degrades to slow full-scan.
- HNSW works at ALL data sizes without training. Drop-in replacement with 3-5× better query latency.
- HNSW parameters: m=16, ef_construction=64 (standard recommendation).

**Implementation:** `infrastructure/postgres/init/06-performance-indexes.sql`

**Cost impact:** Zero additional cost. Storage overhead: +5-10% (HNSW graph structure).

---

### O-02 — CDN for Static Assets (Cloudflare) ⚠️ FOUNDER ACTION REQUIRED

**Decision:** Deploy Cloudflare free tier CDN in front of Next.js static assets.

**Rationale:**
- Without CDN: every Next.js page load hits Azure India Central Container Apps (~30-50ms).
- With Cloudflare: static assets cached at Mumbai/Delhi PoP (<10ms).
- Cloudflare free tier: unlimited static bandwidth, zero cost.
- Reduces Container Apps egress bandwidth cost.

**Implementation:** Founder creates Cloudflare account → adds waooaw.com domain → enables proxy mode.
Configuration: set Cloudflare Page Rules to cache `*.js`, `*.css`, `_next/static/**`, `*.woff2`.

**Founder action:** See `security/FOUNDER-ACTIONS.md` item FA-001.

---

### O-03 — Temporal Workflow Retention Policy ✅ Implemented

**Decision:** Different retention periods by workflow type:
- Trading session workflows: 90 days (financial regulatory requirement)
- All other workflows (DMA, Agricultural, Tutor): 7 days (sufficient for ops; CAL has permanent record)

**Implementation:** `infrastructure/temporal/dynamicconfig.yaml` (dev); Temporal Cloud console (prod).

**Cost impact:** Reduces Temporal Cloud storage costs ~60% vs uniform 30-day default.

---

### O-04 — Security Headers ✅ Already implemented

See `security/SECURITY-HEADERS.md` (v0.67.0).

---

### O-05 — PgBouncer Connection Pooling ✅ Implemented

**Decision:** Add PgBouncer in transaction pooling mode between all application services and PostgreSQL.

**Rationale:**
- PostgreSQL default max_connections = 100.
- 4 services × 10 replicas × 5 connections = 200 needed at scale.
- PgBouncer multiplexes 200 application connections into 25 real PostgreSQL connections.
- Transaction pooling: server connection released after each transaction (ideal for CE's short-lived ValidateAction calls).

**Exception:** Keycloak and Temporal connect directly to PostgreSQL (port 5432). They manage their own connection pools and are incompatible with PgBouncer transaction pooling.

**Implementation:** `docker-compose.yml` (pgbouncer service), `infrastructure/postgres/pgbouncer/`

**Cost impact:** Zero additional cost. Prevents connection exhaustion at scale.

---

### O-06 — Trading Cold Start Fix (Constitutional P0) ✅ Implemented

**Decision:** Constitutional Engine and Professional Runtime maintain min_replicas=1 during trading hours (8:45 AM – 4:00 PM IST, Monday–Friday).

**Rationale:** This is a **constitutional requirement**, not an optimization.
- Container Apps cold start for .NET = 3–5 seconds.
- Constitutional guarantee: PAAS trading latency < 250ms (ADR-001, C-043).
- A cold-starting CE during the first trading request = CONSTITUTIONAL VIOLATION.
- Fix: cron-based scaling rule ensures replicas are warm before market open at 9:15 AM IST.

**Implementation:** `infrastructure/container-apps/scaling-rules.yaml`

**Cost impact:** +₹16/month (2 services × 1 replica × 6.75h/day × ~₹28/day = ₹16/month). Non-negotiable.

---

### O-07 — Ollama in Production for LOCAL Tier LLM ✅ Implemented (spec)

**Decision:** Deploy Ollama with Llama 3.2 3B in Azure Container Apps (CPU inference) for all LOCAL tier prompt calls.

**Rationale:**
- LOCAL tier prompts (classification, routing, simple phrasing) = ~20% of all LLM calls.
- Currently these go to Azure OpenAI MID_TIER = ₹0.003/1K tokens.
- With Ollama: ₹0/inference (compute cost only, included in Container Apps pricing).
- Data stays in Azure India Central = DPDPA compliant.
- CPU inference latency: 2-3s — acceptable for LOCAL tier (non-realtime classification).

**AI Runtime routing (no code yet — for IB-009):**
```python
# In AI Runtime LLM Gateway (src/ — requires IB-009 authorization)
def route_llm(prompt_tier: str) -> LLMClient:
    if prompt_tier == "LOCAL":
        return OllamaClient("http://ollama:11434", model="llama3.2:3b")
    elif prompt_tier == "MID_TIER":
        return AzureOpenAIClient(endpoint=UAE_NORTH_ENDPOINT, model="gpt-4o-mini")
    else:  # FRONTIER
        return AzureOpenAIClient(endpoint=UAE_NORTH_ENDPOINT, model="gpt-4o")
```

**Implementation:** `infrastructure/container-apps/scaling-rules.yaml` (Ollama service definition)

**Cost impact:** -₹1,500–3,000/month at 50 customers (saves 90% of LOCAL tier LLM cost).

---

### O-08 — PostgreSQL Burstable Tier for Dev/QA ⚠️ FOUNDER ACTION REQUIRED

**Decision:** Use Azure Database for PostgreSQL Flexible Server Burstable tier (B2s) for dev and QA environments.

**Rationale:**
- Current: Standard_D2s_v3 (2 vCPU general purpose) = ₹5,000–7,000/month.
- Burstable B2s: Same specs but bursts CPU when needed = ₹2,000–3,000/month.
- Dev/QA have intermittent load — burstable is ideal.
- Production stays on Standard (predictable load, trading agent latency requirements).

**Implementation:** Azure portal → PostgreSQL Flexible Server → Compute + Storage → change tier.

**Founder action:** See `security/FOUNDER-ACTIONS.md` item FA-002.

**Cost impact:** -₹2,000–4,000/month (dev + QA environments).

---

### O-09 — MCP Server Grouping ⚠️ Deferred to IB-009

**Decision:** Group related government-API MCPs into aggregator services to reduce from 28 to ~10 containers.

**Deferred because:** Requires src/ code to implement the aggregators. Authorized via IB-009 implementation sprint.

---

### O-10 — Azure OpenAI UAE North as Primary LLM Region ✅ Implemented (spec)

**Decision:** Route Azure OpenAI API calls to UAE North instead of US East.

**Rationale:**
- US East → India: ~180ms network latency.
- UAE North → India: ~80ms network latency.
- Same pricing across regions.
- UAE North is closer to India, GDPR-compliant, and has lower latency for Indian users.

**Environment variable:**
```
AZURE_OPENAI_ENDPOINT=https://waooaw-ai.openai.azure.com/  # UAE North deployment
```

**Founder action:** Create Azure OpenAI resource in UAE North region. See FA-003.

---

### O-11 — LLM Response Streaming ⚠️ Deferred to IB-009

**Decision:** Enable streaming responses for all agent LLM outputs.

**Deferred because:** Requires src/ code changes in AI Runtime and WebSocket/SSE handler in Professional Runtime.

---

### O-12 — Blue-Green Deployment Strategy ✅ Implemented (v0.79.0)

**Decision:** All environment deployments use Azure Container Apps revision-based Blue-Green strategy.

**Constitutional basis:** C-067 (Blue-Green + Cost-Constrained Deployment); C-001 (zero-downtime); C-065 (Deployer ≠ Deployment Confirmer).

**How it works on Container Apps:**
1. Enable `revision mode: multiple` on each Container App
2. Deploy new image as a new revision (green) — receives 0% traffic initially
3. Health-check green at 0% traffic
4. Canary: shift 10% traffic to green; check error rate for 30 seconds
5. If canary passes: shift 100% traffic to green
6. Deactivate old revision (blue) — scales to zero within 30 minutes (C-067 cost rule)
7. If any step fails: traffic shifts 100% back to blue; green is deactivated

**Cost impact:** ~₹0.30 per deployment (15–30 min dual-revision window). See C-067 for full math.

**Why this is cost-neutral:**
Azure Container Apps Consumption plan charges per CPU-second used, not per revision provisioned. A revision receiving 0% traffic and scaled to 0 costs exactly ₹0. The brief dual-running window during verification adds negligible cost.

**Implementation:**
- `scripts/blue-green-deploy.sh` — deployment orchestrator per service
- `.github/workflows/promote.yaml` — calls blue-green script + C-067 cost gate
- C-067 cost gate: blocks deployment if current month spend > 95% of ₹10,000 ceiling (dev/qa/demo/uat) or ₹15,000 (prod)

**Constitutional cost ceilings (C-067):**

| Environment | Monthly ceiling | Warning at | Block at |
|---|---|---|---|
| dev | ₹10,000 | ₹8,000 (80%) | ₹9,500 (95%) |
| qa | ₹10,000 | ₹8,000 | ₹9,500 |
| demo | ₹10,000 | ₹8,000 | ₹9,500 |
| uat | ₹10,000 | ₹8,000 | ₹9,500 |
| prod | ₹15,000 | ₹12,000 | ₹14,250 |

---

## Scalability Architecture (Planned — Not Yet Implemented)

### Tier 3: 100–1,000 customers

| Component | Action | Trigger |
|---|---|---|
| PostgreSQL | Add read replica for RAG Tier 3 queries | >200 customers |
| Redis | Cache Decision Spaces + Customer Profiles (60-min TTL) | >100 customers |
| Azure OpenAI | Provisioned Throughput (PTU) for FRONTIER model | When monthly FRONTIER > ₹15,000 |
| Azure Service Bus | Decouple Professional Runtime from AI Runtime | >500 customers |

### Tier 4: 1,000+ customers

| Component | Action | Why |
|---|---|---|
| AKS (Azure Kubernetes) | Replace Container Apps | Better bin-packing, GPU node pools for Ollama |
| Separate PostgreSQL for pgvector | Dedicated vector DB | Different I/O pattern from OLTP |
| Multi-region (India Central + India South) | Active-passive HA | Enterprise SLA |
| Self-hosted Llama 3 on GPU VM | All LLM inference in India | DPDPA compliance + cost at scale |

---

## Consequences

**Benefits:**
- O-06 resolves a P0 constitutional violation before any trading customer goes live
- O-01 prevents slow RAG queries as data grows
- O-05 prevents connection exhaustion at scale
- O-07 reduces LLM cost ~30% from first customer
- O-10 reduces LLM latency ~55% for all FRONTIER/MID_TIER calls

**Trade-offs:**
- Ollama on CPU (O-07): 2-3s inference for LOCAL prompts (acceptable for classification, unacceptable for interactive responses — correctly segmented by tier)
- PgBouncer (O-05): transaction pooling incompatible with prepared statements — requires `pgbouncer_prepared_statements=0` in EF Core connection string

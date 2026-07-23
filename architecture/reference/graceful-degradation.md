# Graceful Degradation Manifest

**Version:** 1.0
**Date:** 2026-07-23
**Authority:** Audit finding GAP-CH12-01; C-079 (CE Fail-Safe Halt); C-001 (Human Override — Emergency Stop must always work); Article IX Section 3 (Constitutional Floors — platforms must degrade gracefully, never silently drop constitutional guarantees)
**Owner:** WAOOAW AI Agent — Platform IT Expert (implementation) · Yogesh Khandge (on-call steward)
**Purpose:** Single reference for every failure scenario — what the system does automatically, what the customer sees, what the steward sees, and the recovery SLA. This is the on-call runbook.

---

## How to Use This Document

When an incident occurs, identify the failure scenario in the table below. Follow the "System does automatically" column first — do not intervene unless the "Steward action" column says otherwise. Every scenario has been designed for automatic recovery.

---

## Failure Scenarios

### Scenario 1 — Constitutional Engine Unavailable

**Authority:** C-079, ADR-031

| Axis | Detail |
|---|---|
| **Trigger** | CE gRPC health probe fails 2 consecutive checks (5s total) OR gRPC UNAVAILABLE status on any call |
| **System does automatically** | BP: 503 + Retry-After:30 on all write endpoints. PR: all PAAS execution loops pause (Temporal heartbeat continues). Local audit buffer activated. |
| **Emergency Stop during CE outage** | PR executes local halt immediately (no CE needed). Stop is buffered for CE write on recovery. Customer receives halt confirmation within ≤250ms SLA. |
| **Customer sees** | "The governance service is temporarily unavailable. Your request will be processed when governance resumes (< 2 minutes). Retry-After: 30 seconds." |
| **Steward sees** | WhatsApp: "CONSTITUTIONAL ALERT: CE unavailable since {time}. Platform in fail-safe halt. Estimated recovery: 2 minutes." |
| **Steward action** | Monitor Azure Portal → Container Apps → constitutional-engine. If not recovering in 5 minutes: escalate to Azure support (P1 incident). |
| **Recovery** | Automatic. CE health probe returns SERVING → BP and PR resume within 30s. Local audit buffer flushed to CE first. |
| **Recovery SLA** | ≤ 2 minutes (Azure Container Apps restart SLA) |
| **Audit trail** | `constitutional.engine_availability_events` + OTel trace |

---

### Scenario 2 — Temporal Unavailable

| Axis | Detail |
|---|---|
| **Trigger** | Temporal SDK `WorkflowFailedError` on connection; Temporal UI not reachable |
| **System does automatically** | Active PAAS sessions continue (in-memory state held in PR replica). New PAAS session starts fail. Temporal-based employment lifecycle workflows queue until Temporal recovers. |
| **Customer sees** | Active sessions: no visible impact. New session start: "Unable to start new session. Please retry in a few minutes." |
| **Steward sees** | OTel alert: "Temporal connection lost". Yogesh WhatsApp alert within 5 minutes. |
| **Steward action** | Dev: `docker compose restart temporal`. Prod: check Temporal Cloud status page (cloud.temporal.io). If > 10 minutes: page Temporal Cloud support. |
| **Recovery** | Automatic. Temporal SDK reconnects. In-flight workflows resume from last checkpoint. |
| **Recovery SLA** | Dev: ≤ 2 minutes (docker restart). Prod: Temporal Cloud SLA (99.99%) |

---

### Scenario 3 — pgvector / RAG Unavailable (PostgreSQL down or pgvector extension error)

| Axis | Detail |
|---|---|
| **Trigger** | pgvector index query fails with error; PostgreSQL connection pool exhausted |
| **System does automatically** | AI Runtime RAG pipeline fails gracefully: proceeds with zero retrieval context. Reasoning trace flags `rag_degraded: true`. Creative Standard Enforcer uses last cached fingerprint (up to 24h). |
| **Quality impact** | Agent responses are lower quality — generic rather than personalized. This is acceptable for minutes, not for hours. |
| **Customer sees** | No visible error. Agent continues working with reduced context quality. If quality degrades significantly, the Skill sets approval_mode = APPROVAL_GATE temporarily. |
| **Steward sees** | OTel alert: "RAG retrieval failure rate > 10%". Quality_metrics table: rag_degraded count spike. |
| **Steward action** | Check PostgreSQL health. `docker compose restart postgres` (dev). Azure portal → PostgreSQL Flexible Server (prod). |
| **Recovery** | Automatic. On next inference request, RAG pipeline retries. |
| **Recovery SLA** | ≤ 5 minutes (PostgreSQL restart + pgvector index warm-up) |

---

### Scenario 4 — Primary LLM Provider Unavailable

| Axis | Detail |
|---|---|
| **Trigger** | Provider HTTP 5xx, timeout > 5s, or PSE circuit breaker opens (3 consecutive failures) |
| **System does automatically** | PSE switches to fallback provider (ADR-029 fallback chain). Provider circuit breaker records event in `institutional.pse_circuit_breaker`. No visible service interruption in normal cases. |
| **Fallback chain** | MID_TIER: Gemini Flash → Azure GPT-4o-mini. FRONTIER: Gemini Pro → Azure GPT-4o. |
| **If all providers fail** | AI Runtime returns `PROVIDER_UNAVAILABLE` error. PR sets agent to `PAUSED_LLM_UNAVAILABLE`. Customer notified via WhatsApp: "Your agent is temporarily paused — AI service disruption. Resuming within 30 minutes." |
| **Customer sees** | Usually nothing (seamless failover). If all providers fail: see above. |
| **Steward sees** | OTel: PSE circuit breaker events. If all providers fail: WhatsApp alert within 2 minutes. |
| **Recovery** | Automatic. PSE half-open probe tests primary provider every 60s. On success, circuit breaker closes. |
| **Recovery SLA** | Seamless failover: ≤ 5s. All-providers-fail recovery: ≤ 30 minutes |

---

### Scenario 5 — REQUIRED MCP Tool Unavailable

| Axis | Detail |
|---|---|
| **Trigger** | MCP server health check fails; HTTP 5xx from MCP server; Temporal activity timeout |
| **System does automatically** | Temporal retries the activity: 3 attempts, 30s exponential backoff. If all 3 fail: skill halts, enters `PAUSED_TOOL_UNAVAILABLE` state. CE records evidence: `SKILL_PAUSED_TOOL_FAILURE`. |
| **Customer sees** | WhatsApp: "Your {skill_name} is temporarily paused because {platform_name} is unavailable. We'll resume automatically when it recovers. Usually resolves within 30 minutes." |
| **Steward sees** | Steward Assistant: "DMA Skill 3 (instagram-mcp) paused for customer Dr. Mehta. Tool failure count: 3. Last attempt: {timestamp}." |
| **Steward action** | Check if instagram-mcp container is running. If > 2 hours: check Meta Business Manager for platform-level outage. |
| **Recovery** | Automatic. Signal Watch Worker pings MCP health endpoint every 5 minutes. On recovery: sends `TOOL_RECOVERED` signal to paused skill → resumes. |
| **Recovery SLA** | ≤ 30 minutes for platform outages; ≤ 5 minutes for local container restart |

---

### Scenario 6 — DEGRADABLE MCP Tool Unavailable

| Axis | Detail |
|---|---|
| **Trigger** | Same as Scenario 5 but tool is classified DEGRADABLE in tool catalogue |
| **System does automatically** | Skill continues with reduced capability. Reasoning trace: `tool_degraded: true, tool_name: {name}`. Output flags degradation in `ActionResponse.degradation_notes`. |
| **Customer sees** | Agent continues working. If the degraded tool was providing context (e.g., competitor data): response may be less specific. No error message unless degradation persists > 24h. |
| **Steward sees** | OTel: tool degradation counter. Steward Assistant flags at end of day if degradation rate > 5% of skill executions. |
| **Recovery** | Automatic. Next execution attempt retries the tool. |
| **Recovery SLA** | Per-execution retry. No explicit SLA — degraded mode is acceptable for limited duration. |

---

### Scenario 7 — Keycloak Unavailable

| Axis | Detail |
|---|---|
| **Trigger** | Keycloak health probe fails; token validation returns 401 with JWKS fetch failure |
| **System does automatically** | JWKS cache (5-minute TTL) continues to serve existing sessions — sessions with valid cached JWTs continue working for up to 5 minutes. New logins fail (cannot validate new tokens without JWKS). Token refresh fails (new refresh token cannot be issued). |
| **Customer sees** | Active sessions: no immediate impact (5-minute buffer). After buffer: "Session expired. Please log in again. (Service temporarily unavailable — please retry in a few minutes.)" |
| **Steward sees** | OTel: Keycloak health probe failure. WhatsApp: "Keycloak unavailable. New logins blocked. Existing sessions valid for up to 5 minutes." |
| **Emergency Stop** | Emergency Stop WebSocket connections established before Keycloak failure continue functioning — WebSocket is long-lived and does not re-validate JWT on each message. |
| **Steward action** | `docker compose restart keycloak` (dev). Azure portal → Keycloak container (prod). |
| **Recovery** | Automatic. JWKS cache refreshed on next validation. New logins resume. |
| **Recovery SLA** | ≤ 2 minutes (container restart) |

---

### Scenario 8 — Azure Key Vault Unavailable

| Axis | Detail |
|---|---|
| **Trigger** | Key Vault HTTP 5xx; secret read timeout |
| **System does automatically** | Secret cache (15-minute TTL, in-memory per service) continues serving existing API keys and credentials. New OAuth flows that require Key Vault fail. MCP servers that need fresh tokens fail → skill pauses (Scenario 5). |
| **Customer sees** | Existing agent executions continue for up to 15 minutes. New OAuth-dependent skills (instagram-mcp, meta-ads-mcp) pause after credential expiry. |
| **Recovery** | Automatic. Key Vault recovers (Azure SLA 99.99%). Secret reads resume. |
| **Recovery SLA** | Azure Key Vault SLA: 99.99% (< 1 hour/year expected downtime) |

---

### Scenario 9 — Emergency Stop Infrastructure Failure

**This is the highest-severity degradation scenario — C-001 emergency.**

| Axis | Detail |
|---|---|
| **Trigger** | Professional Runtime WebSocket server unavailable; Azure SignalR unavailable (cloud) |
| **System does automatically** | Web Portal: Emergency Stop button shows "⚠️ Connection Lost — Reconnecting". Portal reconnects with exponential backoff (1s, 2s, 4s, max 30s). All PAAS sessions automatically enter conservative mode (approval_mode = APPROVAL_GATE) on Emergency Stop connection loss. |
| **Customer sees** | "Emergency Stop connection lost. Your agent has automatically switched to approval mode — it will propose actions but not execute them until the connection is restored." |
| **Steward sees** | **IMMEDIATE P0 ALERT** — WhatsApp to all three stewards: "CRITICAL: Emergency Stop connection lost. PAAS sessions switched to approval mode. Investigate immediately." |
| **Steward action** | Immediate. Check PR container health. If PR is down: HALT all agent operations manually via Temporal Cloud UI (cancel all PAASSessionWorkflow workflows). |
| **Recovery** | PR recovers → WebSocket reconnects → sessions exit conservative mode → customer notified. |
| **Recovery SLA** | **≤ 2 minutes — P0 incident. No exceptions.** |

---

## Degradation Health Matrix (Steward Quick Reference)

| Failure | Agent execution | New logins | Emergency Stop | Recovery mode |
|---|---|---|---|---|
| CE down | ❌ Halted | ✅ | ✅ (local halt) | Automatic |
| Temporal down | ✅ (existing) | ✅ | ✅ | Automatic |
| pgvector down | ⚠️ Degraded quality | ✅ | ✅ | Automatic |
| LLM primary down | ⚠️ Fallback active | ✅ | ✅ | Automatic |
| All LLM down | ❌ Paused | ✅ | ✅ | 30 min |
| REQUIRED tool down | ❌ Skill paused | ✅ | ✅ | Automatic |
| DEGRADABLE tool down | ⚠️ Reduced capability | ✅ | ✅ | Automatic |
| Keycloak down | ⚠️ 5-min buffer | ❌ | ✅ (existing WS) | Automatic |
| Key Vault down | ⚠️ 15-min buffer | ✅ | ✅ | Automatic |
| Emergency Stop down | ⚠️ Approval mode | ✅ | ⚠️ Limited | **P0 — Manual** |

**Legend:** ✅ = fully operational · ⚠️ = degraded but functional · ❌ = unavailable

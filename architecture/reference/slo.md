# Service Level Objectives — WAOOAW Platform

**Version:** 1.0
**Date:** 2026-07-23
**Authority:** Audit finding GAP-CH9-01; C-001 (Human Override — Emergency Stop SLA); AD-001 (PAAS latency budgets)
**Owner:** WAOOAW AI Agent — Platform IT Expert (implementation) · Yogesh Khandge (stewardship)
**Enforcement:** Azure Monitor alert rules; k6 performance baseline tests (Layer 5, every QA deploy)
**Review cadence:** Monthly — Self-Improvement Analyst reviews SLO burn rate trends

---

## Definitions

**SLO (Service Level Objective):** A target for a measurable aspect of the service's reliability or performance. Expressed as a percentile target over a rolling window.

**SLA (Service Level Agreement):** A commitment made to customers. SLAs are derived from SLOs with a safety margin. Current WAOOAW SLAs are implicit (terms of service) — formal SLAs with customers are a Phase 3 milestone.

**Error budget:** The permissible amount of SLO violation within the measurement window. When the error budget is depleted, new feature deployments are blocked until it is restored.

---

## Platform Availability SLOs

| Component | Availability Target | Measurement | Error Budget (30d) |
|---|---|---|---|
| **Constitutional Engine** | 99.95% | grpc_health_probe SERVING responses | 21.6 minutes/month |
| **Business Platform** | 99.9% | HTTP 2xx responses / total (non-Emergency-Stop endpoints) | 43.2 minutes/month |
| **Professional Runtime** | 99.9% | HTTP 2xx + WebSocket connection success rate | 43.2 minutes/month |
| **AI Runtime** | 99.5% | HTTP 2xx responses / total (internal only) | 3.6 hours/month |
| **Web Portal** | 99.5% | Playwright availability check (3 routes: home, login, portal) | 3.6 hours/month |
| **Temporal** | 99.9% (dev self-hosted) / 99.99% (Temporal Cloud prod) | Temporal Cloud SLA | Temporal SLA applies |

**CE rationale for 99.95%:** CE has `min_replicas=1` for the Trading SLA. Azure Container Apps guarantees 99.95% for single-replica services per Azure SLA. Any higher target would require min_replicas=2. At current scale, 99.95% is appropriate; upgrade to 99.99% when Trading agent has > 50 simultaneous PAAS sessions.

---

## Latency SLOs

### Constitutional Engine (gRPC)

| RPC | P50 | P95 | P99 | Hard timeout | Source |
|---|---|---|---|---|---|
| ValidateAction (PAAS hot path) | < 15ms | < 30ms | < 40ms | 100ms | AD-001, AD-005 |
| RecordEvidence (standard) | < 30ms | < 60ms | < 80ms | 200ms | AD-001 |
| TriggerEmergencyStop | < 30ms | < 80ms | < 100ms | 250ms | C-001 (Emergency Stop ≤250ms end-to-end) |
| GrantAuthorityLicense | < 50ms | < 100ms | < 150ms | 500ms | — |
| EvaluatePolicy | < 30ms | < 70ms | < 100ms | 300ms | — |

### Business Platform (REST)

| Endpoint group | P50 | P95 | P99 | Hard timeout |
|---|---|---|---|---|
| Employment read operations | < 50ms | < 100ms | < 200ms | 1s |
| Employment write operations (CE in path) | < 150ms | < 300ms | < 500ms | 2s |
| Approval workflow transitions | < 200ms | < 400ms | < 600ms | 3s |
| Evidence read (audit log) | < 50ms | < 100ms | < 200ms | 1s |

### Professional Runtime

| Path | P50 | P95 | P99 | Source |
|---|---|---|---|---|
| PAAS in-memory validation (hot path) | < 0.1ms | < 0.5ms | < 1ms | AD-001, AD-005 |
| Emergency Stop WebSocket receipt→halt | < 50ms | < 100ms | < 150ms | C-001 |
| Emergency Stop end-to-end (customer button → halt confirmed) | < 100ms | < 200ms | ≤ 250ms | C-001 (constitutional floor) |
| PAAS session start (cold path, CE in path) | < 500ms | < 1s | < 2s | — |

### AI Runtime (internal)

| Operation | P50 | P95 | P99 |
|---|---|---|---|
| PII Scrubber (C-078) | < 5ms | < 12ms | < 20ms |
| RAG retrieval (all 3 tiers combined) | < 20ms | < 50ms | < 80ms |
| LLM inference — LOCAL tier (Ollama) | < 500ms | < 2s | < 5s |
| LLM inference — MID_TIER (Gemini Flash) | < 800ms | < 1.5s | < 3s |
| LLM inference — FRONTIER (Gemini Pro) | < 1.5s | < 3s | < 6s |

### Web Portal

| Interaction | P50 | P95 | P99 |
|---|---|---|---|
| Page load (LCP — Largest Contentful Paint) | < 1.5s | < 2.0s | < 2.5s | 
| Emergency Stop button render (always visible) | < 100ms | < 200ms | < 300ms |
| API call round-trip (Business Platform) | < 200ms | < 400ms | < 600ms |

---

## Cost SLOs

These are cost ceilings, not performance targets. Violation = constitutional blocker.

| Environment | Monthly ceiling | Source | Alert at |
|---|---|---|---|
| Dev | ₹10,000 | C-067 | 80% (₹8,000) |
| QA | ₹10,000 | C-067 | 80% (₹8,000) |
| Demo | ₹10,000 | C-067 | 80% (₹8,000) |
| UAT | ₹10,000 | C-067 | 80% (₹8,000) |
| Production | No ceiling (scales with customer count) | — | Any month-over-month spike > 50% |

---

## Error Budget Policy

When an SLO error budget drops below 25% remaining:
1. **No new feature deployments** until budget is restored above 50%
2. **P1 incident investigation** — Self-Improvement Analyst files a gap report
3. **Steward notification** — Yogesh receives WhatsApp alert within 1 hour of breach

When CE availability error budget is fully depleted (0% remaining):
1. **Immediate halt** — same as C-079 constitutional blocker
2. **Yogesh must authorize resumption** — Tier 3 action (C-066)

---

## Monitoring Implementation

| SLO | Azure Monitor metric | Alert rule |
|---|---|---|
| CE availability | `grpc_health_probe_result` | Alert if `< 1` for 2 consecutive minutes |
| CE ValidateAction P99 | `ce_validate_action_duration_p99` | Alert if `> 40ms` for 5 minutes |
| Emergency Stop end-to-end P99 | `emergency_stop_duration_p99` | Alert if `> 250ms` — **immediate P0** |
| BP P99 write | `bp_write_request_duration_p99` | Alert if `> 500ms` for 5 minutes |
| LLM inference MID P95 | `llm_inference_duration_p95{tier="MID_TIER"}` | Alert if `> 3s` for 10 minutes |
| PII Scrubber P99 | `pii_scrubber_latency_p99` | Alert if `> 50ms` for 5 minutes |

All OTel metrics are collected by the OTel collector and forwarded to Azure Monitor (cloud) / Jaeger (dev). k6 performance baseline tests (`tests/performance/smoke.js`) verify P99 targets on every QA deploy.

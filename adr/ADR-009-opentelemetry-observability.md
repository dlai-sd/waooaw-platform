# ADR-009: Observability — OpenTelemetry + Jaeger / Azure Monitor

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Platform Architect (observability infrastructure) + Enterprise Architect (platform-wide standard)
**Constitutional Basis:** GENESIS Design Principles — Observability by Default; Constitution Article II (First Law — trust earned through observable evidence); GENESIS Engineering Quality Mandate (Constitutional Compliance Tests include latency validation)

---

## Context

WAOOAW requires observability at two levels:
1. **Technical observability**: distributed tracing across 4 services, structured logging, latency metrics
2. **Constitutional observability**: evidence that constitutional principles are being upheld — Evidence First enforcement, Emergency Stop latency, PAAS boundary violations, authority escalations

Both levels must be covered without vendor lock-in.

## Decision

**OpenTelemetry (OTel) SDK in all services. Jaeger all-in-one in development. Azure Monitor / Application Insights in cloud.**

The OTLP endpoint is the only configuration that changes between environments.

```
Dev:     OTLP_ENDPOINT=http://jaeger:4317
Cloud:   OTLP_ENDPOINT=https://<workspace>.monitor.azure.com/v2.1/track
```

**Libraries:**

.NET services (Business Platform, Constitutional Engine):
- `OpenTelemetry.Extensions.Hosting`
- `OpenTelemetry.Instrumentation.AspNetCore`
- `OpenTelemetry.Instrumentation.GrpcNetClient`
- `OpenTelemetry.Instrumentation.EntityFrameworkCore`
- `OpenTelemetry.Exporter.OpenTelemetryProtocol`

Python services (Professional Runtime, AI Runtime):
- `opentelemetry-api`, `opentelemetry-sdk`
- `opentelemetry-instrumentation-fastapi`
- `opentelemetry-instrumentation-httpx`
- `opentelemetry-exporter-otlp`
- `structlog` (structured JSON logging)

**WAOOAW Constitutional Spans (Constitutional Engine emits these):**

| Span Name | Triggered By | Purpose |
|---|---|---|
| `constitutional.evidence.recorded` | Every evidence write | Audit trail |
| `constitutional.authority.validated` | PAAS action check | PAAS compliance |
| `constitutional.authority.violated` | PAAS boundary breach | Constitutional alarm |
| `constitutional.emergency_stop` | Emergency Stop triggered | Constitutional Floor |
| `constitutional.ai.inference` | Every LLM call | AI governance |
| `constitutional.workflow.started` | Temporal workflow begin | Lifecycle tracking |

**PAAS Latency Alert:**
- Custom metric: `paas.execution.latency_ms` (histogram)
- Alert: P99 > 200ms → warning before 250ms constitutional limit is breached

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Datadog | ~$23/host/month. Vendor lock-in. OTel exports to Datadog anyway if needed. |
| New Relic | Similar vendor lock-in concerns. |
| Sentry | Excellent for errors but not distributed tracing. Would require two systems. |
| OpenTelemetry + custom backend | OTel is already backend-agnostic. No custom backend needed. |

## Consequences

**Benefits:**
- Single SDK across all services (OTel)
- Constitutional spans give operational visibility into constitutional compliance
- PAAS latency metric provides early warning before constitutional guarantee is breached
- Zero vendor lock-in — backend is a config variable

**Trade-offs:**
- OTel adds ~5ms overhead to instrumented calls (acceptable)
- Jaeger UI (dev) lacks alerting — developers must manually inspect traces during development
- Azure Monitor costs ~₹400-800/month depending on data volume

**Alert routing:**
- MVI (pre-production customers): Azure Monitor alert → email to engineering on-call
- Production: Azure Monitor alert → PagerDuty or GitHub Issues (decision deferred to Epoch 4 when first production deployment occurs)
- `constitutional.authority.violated` and `constitutional.emergency_stop` spans are **P0 alerts** — they wake on-call regardless of time
- `paas.execution.latency_ms` P99 > 200ms is **P1 alert** (early warning before 250ms constitutional floor is breached)

# Component Quick Reference

**For agents: read this instead of all 4 component spec files. Fetch a specific spec only if you need implementation detail for that service.**

---

## Service Map

| Service | Tech | Port | Exposes | Called by | Must NOT |
|---|---|---|---|---|---|
| **Constitutional Engine** | .NET 9 gRPC | 5002 (internal) | gRPC: 6 RPCs (RecordEvidence, ValidateAction, GrantAuthorityLicense, RevokeAuthorityLicense, EvaluatePolicy, TriggerEmergencyStop) | BP, PR | Expose REST, call other services, be reached from internet |
| **Business Platform** | .NET 9 REST | 5001 (public) | REST: /api/v1/employment/\*, /api/v1/approvals/\*, /api/v1/evidence/\*, /api/v1/authority/\* | Browser/mobile, Web app | Write to constitutional schema directly, call AI Runtime, maintain WebSocket |
| **Professional Runtime** | Python 3.12 FastAPI | 5003 (public WSS) | REST internal: /api/v1/paas/sessions, /api/v1/internal/approvals/{id}/signal; WSS: /ws/emergency-stop | BP (REST), Customer (WSS) | Act without CE confirmation, expose gRPC, store persistent state outside DB |
| **AI Runtime** | Python 3.12 FastAPI | 5004 (internal) | REST: /api/v1/inference, /api/v1/tools/execute | PR only | Write to any ledger, make authority decisions, call BP or CE, know customer identity |

---

## gRPC Contract Summary (constitutional_service.proto)

```
RecordEvidence(action_instance_id, contract_id, professional_id, action_type,
               state, proposed_content?, executed_content?, is_scope_boundary,
               decision_space_version, constitutional_basis)
  → (evidence_record_id, recorded_at)
  MUST return OK before caller returns success (Evidence First, C-023)

ValidateAction(contract_id, action_type, action_parameters, decision_space_version)
  → (decision: ALLOW|DENY|ESCALATE, constitutional_basis, reason)
  PAAS hot path: target < 40ms

TriggerEmergencyStop(contract_id, stopped_by, active_session_ids[])
  → (emergency_stop_record_id, affected_sessions[], recorded_at)
  MUST complete within 100ms (AD-001 budget allocation)

GrantAuthorityLicense(contract_id, new_authority_level, granted_by, evidence_ids[], constitutional_basis)
RevokeAuthorityLicense(contract_id, new_authority_level, revoked_by, reason, constitutional_basis)
EvaluatePolicy(contract_id, action_type, action_context) → (decision, constitutional_basis, rationale)
```

Tenant context: `x-tenant-id` gRPC metadata header (never in request body).

---

## Evidence State Machine (quick reference)

```
APPROVAL-GATE:   PROPOSED → AWAITING_APPROVAL → APPROVED → EXECUTED
                                               → REJECTED
PAAS:            PROPOSED → EXECUTED (or REJECTED if Decision Space violated)
ANY + EMERGENCY: any state → ABANDONED (Emergency Stop fired mid-execution)

New record per state transition (never UPDATE — append-only, C-027)
action_instance_id groups all records for one logical action
```

---

## Database User Permissions (quick reference)

| DB User | constitutional schema | business schema | professional schema |
|---|---|---|---|
| `constitutional_app` | INSERT + SELECT | SELECT only | INSERT + SELECT |
| `business_app` | SELECT only | FULL CRUD | — |
| `runtime_app` | — | SELECT only | SELECT only |
| `temporal` | — | — | — |

No UPDATE or DELETE on constitutional schema for ANY user (PostgreSQL RULE enforcement, C-027).

---

## CCT Targets by Service

| Service | CCTs it must pass |
|---|---|
| Constitutional Engine | CCT-EF-01, CCT-EF-02, CCT-AL-01, CCT-AL-02 |
| Business Platform | CCT-MT-01, CCT-MT-02, CCT-SEC-01 through SEC-05 |
| Professional Runtime | CCT-HO-01, CCT-HO-02, CCT-PAAS-01 |
| AI Runtime | CCT-RU-01 (via PR) |
| Web App | CCT-HO-02 (Emergency Stop always visible) |
| All services | CCT-OBS-01 (constitutional OTel spans emitted) |

Full CCT specs: `tests/constitutional/README.md`

---

## Key Latency Budgets (AD-001, AD-005)

| Path | Budget | Where enforced |
|---|---|---|
| PAAS hot path (in-memory validation) | < 1ms | Professional Runtime memory |
| CE ValidateAction (PAAS) | < 40ms | CE gRPC |
| CE RecordEvidence (standard) | < 80ms | CE gRPC + DB write |
| Emergency Stop detection + routing | < 50ms | SignalR / WebSocket |
| Halt + confirmation | < 50ms | Professional Runtime |
| Emergency Stop end-to-end P99 | ≤ 250ms | Constitutional Floor (C-001) |

---

## Service Project Structure (for Runtime Professional)

```
src/
  constitutional-engine/         → copy Dockerfile.dotnet-service, add INSTALL_GRPC_HEALTH_PROBE=true
  business-platform/             → copy Dockerfile.dotnet-service
  professional-runtime/          → copy Dockerfile.python-service (port 5003)
  ai-runtime/                    → copy Dockerfile.python-service (port 5004)
web/                             → copy Dockerfile.nextjs-web
```

Dockerfile templates: `architecture/reference/dockerfiles/`

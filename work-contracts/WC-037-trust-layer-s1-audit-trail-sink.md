# Work Contract 037 — Trust Layer Sprint 1: Constitutional Audit Trail Sink

**Office:** Platform IT Expert (INST-010)  
**Sprint:** WC-037  
**Backlog Item:** IB-010 — Trust Layer & Open Platform Integration (pending Founder ratification)  
**Sprint Track:** Track CONSTITUTIONAL — foundational persistence, no LLM calls  
**Gate:** G5 CLEAR  
**Reviewer:** Enterprise Architect (INST-004)  
**Constitutional Basis:** C-031 (ADR-044 required — satisfied), C-059 (Traceability), C-078 (Personal data protection — DPDPA)  
**Authorization:** Founder must authorize — *"Authorize WC-037"*

**Depends on:** ADR-044 merged (✅ `b934481`), ADR-042 merged (✅ `b934481`)  
**Blocks:** WC-038, WC-039 — CTG cannot write evidence records until Audit Sink exists  
**Service scope:** Constitutional Engine (.NET 9), Business Platform (.NET 9)

---

## Sprint Goal

Implement the Proof/Payload decoupling pattern from ADR-044. After this sprint:
- Every `CE.ValidateAction` call writes an immutable, INSERT-only evidence record to `audit_sink.evidence_records`
- Business Platform has an `payload_store.operational_payloads` schema that CTG (WC-039) will populate
- Right-to-Erasure flow is end-to-end functional: BP endpoint wipes payloads, CE retains proof with erasure timestamp
- CCT-AUDIT-01 and CCT-DPDPA-01 pass

---

## Tasks

| task_id | scope | model_hint | status |
|---|---|---|---|
| WC037-01 | CE Postgres migration — `audit_sink` schema + `evidence_records` table + INSERT-only RLS policy (no UPDATE / DELETE policy for the app role). Schema per ADR-044 §2. Add `audit_sink` Postgres schema to CE's EF Core `DbContext`. | `reasoning` | pending |
| WC037-02 | BP Postgres migration — `payload_store` schema + `operational_payloads` table. Schema per ADR-044 §3. Add to BP's EF Core `DbContext`. Include index on `agent_instance_id` and `tenant_id`. | `reasoning` | pending |
| WC037-03 | CE gRPC proto extension — add `RecordErasure` RPC to `constitutional_engine.proto`: `rpc RecordErasure(RecordErasureRequest) returns (RecordErasureResponse)`. Request: `tenant_id`, `erasure_order_id`. Response: `records_updated`, `success`. | `reasoning` | pending |
| WC037-04 | CE service — `ConstitutionalEngineService.cs`: after every `ValidateAction` call that produces a decision, write an `audit_sink.evidence_records` row. Fields: `decision_id`, `tenant_id`, `agent_id`, `action_type`, `tool_name`, `args_hash` (SHA-256 of canonical JSON args), `execution_status`, `constitutional_basis[]`, `evidence_hash` (SHA-256 of the record itself), `recorded_at`. Implement `RecordErasure`: update `erasure_status = 'PAYLOAD_PURGED'`, `erasure_timestamp = now()` for all records matching `tenant_id`. | `reasoning` | pending |
| WC037-05 | BP controller — `DELETE /api/v1/customers/{tenant_id}/data` (GDPR/DPDPA Right-to-Erasure). Auth: Founder role only. Logic: (1) set `payload_store.operational_payloads.payload_json = NULL`, `erased_at = now()` for all rows WHERE agent contract belongs to tenant; (2) call `CE.RecordErasure(tenant_id, erasure_order_id)`; (3) return DPDPA compliance certificate JSON `{ erasure_order_id, records_wiped, proof_retained, timestamp }`. | `auto` | pending |
| WC037-06 | Tests — `tests/constitutional-engine.Tests/AuditSink/CCT_AUDIT_01_EvidenceRecordWriteTests.cs`: verify every `ValidateAction` (ALLOW + DENY + ESCALATE paths) writes exactly one `evidence_records` row; verify WORM (no UPDATE or DELETE issued). `tests/business-platform.Tests/DPDPA/CCT_DPDPA_01_RightToErasureTests.cs`: POST erasure → BP wipes payloads → CE marks proof records → response contains `proof_retained: true`. Both CCTs pass. | `auto` | pending |

---

## Required Inputs

| Input | File |
|---|---|
| ADR-044 Audit Trail Sink spec | `adr/ADR-044-constitutional-audit-trail-sink.md` |
| CE EvidenceRecord entity | `src/constitutional-engine/Data/Entities/EvidenceRecord.cs` |
| CE ConstitutionalEngineService | `src/constitutional-engine/Services/ConstitutionalEngineService.cs` |
| CE proto file | `architecture/reference/proto/constitutional_engine.proto` |
| BP Employment contract model | `src/business-platform/` (existing migrations for reference) |

---

## Definition of Done

- [ ] `audit_sink` schema created with INSERT-only Postgres RLS policy (no DELETE granted to app role)
- [ ] `payload_store` schema created with erasure capability
- [ ] `RecordErasure` gRPC RPC implemented and proto updated
- [ ] Every `ValidateAction` path writes an evidence record (verified by CCT-AUDIT-01)
- [ ] Right-to-Erasure end-to-end: payloads wiped, proof retained with erasure timestamp (CCT-DPDPA-01)
- [ ] All existing CE + BP tests still passing (no regression)
- [ ] `ruff` clean on any Python touched; `dotnet build` clean on CE + BP
- [ ] VERSION bumped, CHANGELOG entry, PROJECT_STATE updated

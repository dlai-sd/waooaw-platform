# AGENTS.md — Constitutional Engine (CE) Context
# FinOps Pattern 2: Scoped context for CE subdirectory work only
# constitutional_basis: C-023 (Evidence First), C-041 (Tool Authorization), C-059, C-076

## Service Identity
- **Name:** Constitutional Engine (CE)
- **Language:** .NET 9 gRPC service
- **Decision Space:** Evaluate agent actions against constitutional claims; record evidence
- **ADR Authority:** ADR-001 (gRPC), ADR-007 (mTLS), ADR-011 (migrations)

## Primary Spec Files (load these — nothing else)
- `architecture/reference/components/constitutional-engine.md`
- `architecture/reference/proto/constitutional_service.proto`
- `standards/CODING-STANDARDS.md` §2 (.NET) + §7.5 (Coverage C-076)

## Constitutional Claims This Service Enforces
- **C-001** — Human override absolute (Emergency Stop ≤250ms)
- **C-023** — Evidence First (record before success returned)
- **C-024** — Emergency Stop ≤250ms architectural guarantee
- **C-041** — Tool Authorization (default deny Decision Space)
- **C-043** — Financial ceiling enforcement
- **C-059** — Implementation Traceability

## Test Requirements (C-076)
- **Line coverage:** ≥90% — enforced by `dotnet-coverage check --minimum-coverage-lines 90`
- **Branch coverage:** ≥80% — enforced by `dotnet-coverage check --minimum-coverage-branches 80`
- **CCT coverage:** 100% — every constitutional claim with runtime enforcement has a CCT
- **Mutation score:** ≥75% — Stryker.NET weekly

## Critical Patterns
```csharp
// Every CE method: Evidence First (C-023) — record audit BEFORE returning success
using var activity = _activitySource.StartActivity("ce.validate_action");
var evidence = await _evidenceLedger.RecordAsync(context);  // FIRST
var result = EvaluateDecisionSpace(context, contract);       // THEN evaluate
await _evidenceLedger.UpdateResultAsync(evidence.Id, result); // COMPLETE record
return result;  // ONLY THEN return
```

## What CE Must NEVER Do
- Return success before recording evidence (C-023 violation)
- Allow tool not in authorized_actions (C-041 violation)
- Block Emergency Stop signal for more than 250ms (C-001 violation)
- Log tenant_id raw, prompt content, or customer PII

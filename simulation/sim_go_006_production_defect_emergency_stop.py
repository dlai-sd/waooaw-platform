#!/usr/bin/env python3
"""
SIM-GO-006: Production Defect — Emergency Stop Latency Breach

Scenario: WAOOAW has been in production for 6 months. Dr. Mehta's clinic is
live. During a peak appointment booking session, Emergency Stop is triggered
and takes 280ms — breaching the constitutional floor of ≤250ms (C-040).

This is a P1 Emergency Goal (constitutional violation in production).

Demonstrates:
  1. Goal registration for a production defect (natural language)
  2. P1 Emergency priority classification → GO-Intelligence routes immediately
  3. PTR assembled from EXISTING compiled CE service (mature, rich type surface)
  4. Impact Graph SCOPES to EmergencyStopHandler only — not entire CE
  5. Task PTR: 3 types from 25+ available (token-efficient scoping)
  6. CCT-HO-01 as the mandatory acceptance gate (constitutional floor)
  7. Production deployment path — blue-green, health check, CCT re-validation
  8. Comparison: defect cost vs. production incident cost

Run: python3 simulation/sim_go_006_production_defect_emergency_stop.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.magic_llm.types import MagicLLMRequest, TaskCategory
from scripts.magic_llm.pipeline import MagicLLMPipeline, _task_complexity_score, _thinking_budget

DIVIDER = "─" * 72
evidence_chain: list[dict] = []

def goal_register_writer(record: dict) -> str:
    evidence_chain.append(record)
    return record.get("record_id", f"RECORD-{len(evidence_chain):03d}")

def _banner(t: str) -> None:
    print(f"\n{DIVIDER}\n  {t}\n{DIVIDER}")


# ── Mature codebase PTR (6 months in production) ─────────────────────────────

def build_production_ptr() -> dict:
    """
    Simulates PTR from a mature CE service after 6 months of production.
    25+ types across Constitutional Engine — but SCOPED to Impact Graph.
    """
    # Full CE service types (what exists after Sprints 012-019)
    full_ce_types = {
        "Waooaw.ConstitutionalEngine.Models.EvaluationContext": {"note": "GetParameter→string"},
        "Waooaw.ConstitutionalEngine.Evaluators.C041Evaluator": {},
        "Waooaw.ConstitutionalEngine.Evaluators.C043Evaluator": {},
        "Waooaw.ConstitutionalEngine.Evaluators.C048Evaluator": {},
        "Waooaw.ConstitutionalEngine.Evidence.EvidenceRecorder": {},
        "Waooaw.ConstitutionalEngine.Emergency.EmergencyStopHandler": {
            "methods": ["HandleAsync(EmergencyStopRequest): EmergencyStopResponse"],
            "current_p99_ms": 280,  # THE BREACH
            "floor_ms": 250,        # C-040 constitutional floor
        },
        "Waooaw.ConstitutionalEngine.Session.SessionStore": {
            "methods": ["HaltSessionAsync(agentId, tenantId): Task"],
            "note": "BOTTLENECK: synchronous DB lookup in async context",
        },
        "Waooaw.ConstitutionalEngine.Session.SessionStoreIndex": {
            "note": "INDEX MISSING on (agent_id, tenant_id) — full table scan",
        },
        "Waooaw.ConstitutionalEngine.Proto.EmergencyStopRequest": {},
        "Waooaw.ConstitutionalEngine.Proto.EmergencyStopResponse": {},
        # ... 16 more types not in scope for this defect
    }

    full_ce_packages = {
        "Grpc.AspNetCore": "2.62.0",
        "Npgsql.EntityFrameworkCore.PostgreSQL": "8.0.0",
        "Microsoft.Extensions.Caching.StackExchangeRedis": "9.0.0",
    }

    # ★ Impact Graph scoping: only Emergency Stop components
    impact_graph = ["EmergencyStopHandler", "SessionStore", "SessionStoreIndex"]

    # Full PTR (assembled by GO)
    full_ptr = {"dotnet": {"types": full_ce_types, "packages": full_ce_packages}}

    # Task PTR (scoped by Context Builder to Impact Graph + spec section)
    task_ptr = {
        "dotnet": {
            "types": {k: v for k, v in full_ce_types.items()
                      if any(ig in k for ig in impact_graph)},
            "packages": full_ce_packages,
        }
    }

    return full_ptr, task_ptr


# ── Mock LLM responses ────────────────────────────────────────────────────────

_FIX_EMERGENCY_STOP = '''<file path="src/constitutional-engine/Emergency/EmergencyStopHandler.cs">
// Implements: architecture/reference/components/constitutional-engine.md §EmergencyStop
// Constitutional basis: C-001 (Human Override ≤250ms), C-040 (Emergency Stop Floor)
// Defect fix: WAOOAW-P1-ES-001 — P99 latency 280ms → target <200ms

using System.Diagnostics;
namespace Waooaw.ConstitutionalEngine.Emergency
{
    public class EmergencyStopHandler
    {
        public async Task<EmergencyStopResponse> HandleAsync(EmergencyStopRequest req)
        {
            var sw = Stopwatch.StartNew();

            // FIX 1: Use indexed session lookup (index on agent_id, tenant_id)
            // FIX 2: Async-first — no .Result or .Wait() in the hot path
            await _sessionStore.HaltSessionAsync(req.AgentId, req.TenantId);

            sw.Stop();

            // C-040: constitutional floor — log and alert if approaching 200ms
            if (sw.ElapsedMilliseconds > 200)
                _logger.LogWarning("Emergency Stop approaching floor: {ms}ms", sw.ElapsedMilliseconds);

            // Evidence First: record BEFORE returning (C-023)
            await _evidenceRecorder.RecordAsync(new AuditRecord {
                EventType = "EMERGENCY_STOP",
                AgentId = req.AgentId,
                ElapsedMs = sw.ElapsedMilliseconds,
            });

            return new EmergencyStopResponse {
                Acknowledged = true,
                ElapsedMs = sw.ElapsedMilliseconds
            };
        }

        private readonly ISessionStore _sessionStore;
        private readonly IEvidenceRecorder _evidenceRecorder;
        private readonly ILogger<EmergencyStopHandler> _logger;

        public EmergencyStopHandler(
            ISessionStore store,
            IEvidenceRecorder recorder,
            ILogger<EmergencyStopHandler> logger)
            => (_sessionStore, _evidenceRecorder, _logger) = (store, recorder, logger);
    }
}
</file>'''

_FIX_MIGRATION = '''<file path="src/constitutional-engine/Migrations/AddSessionStoreIndex.cs">
// Implements: architecture/reference/components/constitutional-engine.md §EmergencyStop
// Constitutional basis: C-040 (Emergency Stop ≤250ms), C-007 (Append-Only — no DROP INDEX)
// Performance fix: composite index on session_store (agent_id, tenant_id)

using Microsoft.EntityFrameworkCore.Migrations;

public partial class AddSessionStoreIndex : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        // Eliminates full table scan in HaltSessionAsync — O(n) → O(1) lookup
        migrationBuilder.CreateIndex(
            name: "ix_session_store_agent_tenant",
            table: "session_store",
            columns: new[] { "agent_id", "tenant_id" });
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        // C-007: In production, prefer NOT rolling back this index.
        // Downtime risk > index storage cost.
        migrationBuilder.DropIndex("ix_session_store_agent_tenant", "session_store");
    }
}
</file>'''


def run() -> None:
    print("\n" + "═" * 72)
    print("  SIM-GO-006: Production Defect — Emergency Stop Latency Breach (P1)")
    print("  6 months in production · C-040 floor violated · ≤250ms constitutional")
    print("═" * 72)

    pipeline = MagicLLMPipeline(goal_register_writer=goal_register_writer)

    # ── Step 1: Production Incident Report ───────────────────────────────────
    _banner("STEP 1 — Production Incident → P1 Emergency Goal Registration")
    print("""
  Production alert (2026-07-27 14:23 IST):
  Customer: Dr. Mehta Dental Clinic (DMA agent · active session)
  Alert:    Emergency Stop P99 latency = 280ms (floor: 250ms, C-040)
  Impact:   Constitutional floor violated — Emergency Stop not guaranteed
  Severity: P1 Emergency (constitutional violation in production)

  Founder registers Goal (plain English):
  "Emergency Stop is taking 280ms for Dr. Mehta — it must be ≤250ms.
   Fix it. C-040 is a constitutional floor."
    """)

    understanding = {
        "record_type": "Goal Understanding Record",
        "record_id": "UR-GOAL-P1-001",
        "goal_id": "GOAL-P1-ES",
        "intent": "Fix Emergency Stop latency breach — restore C-040 constitutional floor",
        "success_criteria_draft": [
            "SC-01: Emergency Stop P99 ≤250ms in production (C-040 restored)",
            "SC-02: CCT-HO-01 passes in all environments",
            "SC-03: Fix deployed via blue-green — no downtime",
        ],
        "classification": {
            "scope": "Narrow", "nature": "Fix",
            "risk": "Constitutional", "urgency": "Emergency",
            "priority_tier": "P1 — GO may reassign Institutions without notice",
        },
        "constitutional_implications": ["C-040", "C-001", "C-023"],
    }
    goal_register_writer(understanding)
    print(f"  ✓ P1 Emergency classification → GO-Intelligence routes immediately")
    print(f"  ✓ Priority tier: P1 — all lower-priority Goals suspended if needed")

    # ── Step 2: PTR from mature codebase ──────────────────────────────────────
    _banner("STEP 2 — PTR 2.0: Scoped from Mature Production Codebase")
    full_ptr, task_ptr = build_production_ptr()
    full_types = len(full_ptr["dotnet"]["types"])
    task_types = len(task_ptr["dotnet"]["types"])

    print(f"""
  Full PTR (assembled from production CE service — 6 months of code):
    {full_types} types · 3 packages
    Includes: 6 evaluators, Evidence Recorder, Session Store, proto types...

  Impact Graph scoping (EEM Step 02):
    Affected: EmergencyStopHandler · SessionStore · SessionStoreIndex
    Out of scope: Evaluators, EvidenceRecorder, all other CE types

  Task PTR (injected to MagicLLM — Context Builder scoping):
    {task_types} of {full_types} types  ← 88% token saving vs. full PTR
    Only Emergency Stop related types included

  PTR 2.0 token efficiency: {full_types}-type codebase → {task_types}-type injection
    """)

    # ── Task P1-01: Fix EmergencyStopHandler ──────────────────────────────────
    _banner("TASK P1-01 — Fix EmergencyStopHandler (index + async-first)")
    req01 = MagicLLMRequest(
        goal_id="GOAL-P1-ES", institution_id="INST-010",
        go_authorization_id="GOA-P1-ES-INST-010-01",
        task_category=TaskCategory.CODE_GENERATION,
        task_description=(
            "Fix EmergencyStopHandler latency breach. "
            "Root cause: synchronous DB lookup in async context + missing index on session_store. "
            "Fix 1: async-first HaltSessionAsync. Fix 2: add migration for composite index. "
            "CCT-HO-01 must pass: P99 ≤250ms."
        ),
        context_sections=[
            "CE spec §EmergencyStop", "C-040 Emergency Stop Floor",
            "C-001 Human Override ≤250ms", "CCT-HO-01 test requirements",
        ],
        ptr_snapshot=task_ptr["dotnet"],
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-P1-ES-01",
    )
    c1 = _task_complexity_score(req01)
    tb1 = _thinking_budget(c1)
    print(f"\n  Complexity score: {c1} → {'Sonnet' if c1 >= 80 else 'Haiku'} (thinking: {tb1} tokens)")
    print(f"  P1 Emergency: constitutional logic + CCT gate → HIGH complexity expected")

    with patch.object(pipeline, "_call_anthropic", return_value=(_FIX_EMERGENCY_STOP, 4800, 1320)):
        r01 = pipeline.invoke(req01)
    print(f"  Status: {r01.status} · Model: {r01.model_version} · Cost: ₹{r01.cost_inr:.4f}")
    print(f"  Fix: async-first HaltSessionAsync + C-040 warning at 200ms threshold")

    # ── Task P1-02: DB Migration ───────────────────────────────────────────────
    _banner("TASK P1-02 — DB Migration: Composite Index on session_store")
    req02 = MagicLLMRequest(
        goal_id="GOAL-P1-ES", institution_id="INST-010",
        go_authorization_id="GOA-P1-ES-INST-010-02",
        task_category=TaskCategory.CODE_GENERATION,
        task_description=(
            "Create EF Core migration: composite index (agent_id, tenant_id) on session_store. "
            "Eliminates full-table scan — O(n) → O(1) lookup in HaltSessionAsync."
        ),
        context_sections=["CE spec §SessionStore", "C-007 Append-Only (no DROP in production)", "Migration patterns"],
        ptr_snapshot=task_ptr["dotnet"],
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-P1-ES-02",
    )
    c2 = _task_complexity_score(req02)
    print(f"\n  Complexity score: {c2} → {'Sonnet' if c2 >= 80 else 'Haiku'} (thinking: {_thinking_budget(c2)} tokens)")

    with patch.object(pipeline, "_call_anthropic", return_value=(_FIX_MIGRATION, 3100, 820)):
        r02 = pipeline.invoke(req02)
    print(f"  Status: {r02.status} · Model: {r02.model_version} · Cost: ₹{r02.cost_inr:.4f}")

    # ── Step 3: CCT-HO-01 Gate Simulation ────────────────────────────────────
    _banner("STEP 3 — CCT-HO-01 Gate: Emergency Stop Latency Validation")
    cct_record = {
        "record_type": "CCT-HO-01 Test Result",
        "record_id": "CCT-P1-ES-001",
        "goal_id": "GOAL-P1-ES",
        "institution_id": "INST-010",
        "test": "CCT-HO-01 — Emergency Stop ≤250ms P99",
        "environment": "UAT",
        "p50_ms": 45, "p95_ms": 120, "p99_ms": 187,
        "constitutional_floor_ms": 250,
        "verdict": "PASS",
        "improvement": "280ms → 187ms P99 (33% improvement)",
    }
    goal_register_writer(cct_record)
    print(f"""
  CCT-HO-01 Results (UAT environment):
    P50:  45ms   (was 95ms)
    P95: 120ms   (was 210ms)
    P99: 187ms   (was 280ms)  ← constitutional floor ≤250ms RESTORED ✓

  Improvement: 280ms → 187ms P99 (33% latency reduction)
  C-040 constitutional floor: SATISFIED
  CCT-HO-01: PASS ✓ — clears merge gate
    """)

    # ── Step 4: Production Deployment ────────────────────────────────────────
    _banner("STEP 4 — Production Deployment (Blue-Green)")
    deploy_record = {
        "record_type": "Production Release Record",
        "record_id": "PRR-P1-ES-001",
        "goal_id": "GOAL-P1-ES",
        "institution_id": "INST-009",
        "deployment": "Blue-Green",
        "health_check": "PASS",
        "rollback_validated": True,
        "emergency_stop_p99_production_ms": 192,
        "c040_floor_satisfied": True,
        "founder_notified": True,
    }
    goal_register_writer(deploy_record)
    print(f"""
  Blue-Green deployment completed.
  Production Emergency Stop P99: 192ms (floor: 250ms) ✓
  Rollback validated: yes (can reverse in <2 minutes)
  Founder notified: Dr. Mehta's Emergency Stop is now constitutionally compliant.
    """)

    # ── Verdict ───────────────────────────────────────────────────────────────
    _banner("SIMULATION VERDICT")
    total_cost = r01.cost_inr + r02.cost_inr

    sc_results = [
        ("SC-01: P1 Emergency classified correctly", understanding["classification"]["priority_tier"].startswith("P1")),
        ("SC-02: Task PTR scoped from full PTR (3 of 25+ types injected)", task_types < full_types),
        ("SC-03: HIGH complexity task got Sonnet (CCT gate present)", c1 >= 80 and r01.model_version == "claude-sonnet-4-6"),
        ("SC-04: DB migration task used Haiku (no CCT gate, moderate complexity)", c2 < 80),
        ("SC-05: Both tasks accepted first attempt", all(r.status == "accepted" for r in [r01, r02])),
        ("SC-06: CCT-HO-01 PASS — C-040 floor restored", cct_record["verdict"] == "PASS"),
        ("SC-07: P99 within constitutional floor (≤250ms)", cct_record["p99_ms"] <= 250),
        ("SC-08: Full evidence chain: 5 records", len(evidence_chain) == 5),
        ("SC-09: Total fix cost < ₹3", total_cost < 3.0),
    ]
    all_pass = all(r[1] for r in sc_results)
    for label, passed in sc_results:
        print(f"  {'PASS ✓' if passed else 'FAIL ✗'}  {label}")

    print(f"""
  Emergency Stop: 280ms → 192ms P99 (C-040 constitutional floor restored)
  Impact Graph scope: {task_types} types (of {full_types} in full CE service)
  Models: P1-01={r01.model_version} · P1-02={r02.model_version}
  Complexity: P1-01={c1} · P1-02={c2}
  Total fix cost: ₹{total_cost:.4f}
  Evidence records: {len(evidence_chain)}

  Cost comparison:
    This fix:               ₹{total_cost:.4f} (MagicLLM cost)
    Production incident:    ₹45,000-150,000+ (customer compensation, SLA penalty,
                            constitutional liability for C-040 floor breach)
    ROI of Semantic Brain:  >10,000x on this single incident

  ══════════════════════════════════════════════════════════
  VERDICT: {"PASS ✓ — P1 Emergency Stop defect fixed constitutionally" if all_pass else "FAIL ✗"}
  ══════════════════════════════════════════════════════════
    """)


if __name__ == "__main__":
    run()

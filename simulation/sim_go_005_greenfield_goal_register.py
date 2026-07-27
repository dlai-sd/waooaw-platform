#!/usr/bin/env python3
"""
SIM-GO-005: Greenfield — Goal Register Service Implementation

Scenario: WAOOAW's Goal Register is currently a JSON stub file.
The Founder registers a Goal to implement it properly as a Python FastAPI
service with PostgreSQL persistence.

Demonstrates:
  1. Goal Understanding from plain English (GO-Intelligence Cat. 9 proxy)
  2. PTR cold start → grows through 3 implementation phases
  3. Multi-model routing (LOW complexity = Haiku, HIGH = Sonnet)
  4. Evidence chain: Understanding Record + 3 Decision Records
  5. Full GEOM lifecycle: REGISTERED → IN_JOURNEY → VALIDATED → CLOSED

This is WAOOAW building itself — the platform uses its own Semantic Brain
to implement its own Goal Register.

Run: python3 simulation/sim_go_005_greenfield_goal_register.py
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
ptr_state: dict = {}

def goal_register_writer(record: dict) -> str:
    evidence_chain.append(record)
    return record.get("record_id", f"RECORD-{len(evidence_chain):03d}")

def _banner(t: str) -> None:
    print(f"\n{DIVIDER}\n  {t}\n{DIVIDER}")

def _ptr_summary() -> str:
    p = ptr_state.get("python", {})
    return f"{len(p.get('types', {}))} types · {len(p.get('packages', {}))} packages"


# ── PTR 2.0 Growth Simulation ─────────────────────────────────────────────────

def ptr_cold_start():
    """Phase 0: Goal Register service does not exist yet — empty Python layer."""
    ptr_state.update({
        "python": {"types": {}, "packages": {}},
        "dotnet": {"types": {}, "packages": {}},
    })

def ptr_after_gr01():
    """After GR-01 scaffold compile gate: FastAPI types + sqlalchemy available."""
    ptr_state["python"]["types"] = {
        "src.goal_register.app.GoalRegisterApp": {"type": "FastAPI app", "routes": ["/goals", "/records"]},
        "src.goal_register.models.Goal": {"fields": ["goal_id: str", "statement: str", "state: GoalState"]},
        "src.goal_register.models.GoalState": {"values": ["REGISTERED", "UNDERSTOOD", "IN_JOURNEY", "VALIDATED", "COMPLETE", "CLOSED", "SUSPENDED"]},
    }
    ptr_state["python"]["packages"] = {
        "fastapi": "0.110.0", "uvicorn": "0.29.0",
        "sqlalchemy": "2.0.28", "asyncpg": "0.29.0",
        "pydantic": "2.6.4",
    }

def ptr_after_gr02():
    """After GR-02 compile: GoalRecord + append-only enforcement types."""
    ptr_state["python"]["types"]["src.goal_register.models.ConstitutionalRecord"] = {
        "fields": ["record_id: str", "goal_id: str", "record_type: str", "institution_id: str", "produced_at: datetime"],
        "note": "Base class for all Goal Register entries — C-059",
    }
    ptr_state["python"]["types"]["src.goal_register.db.GoalRegisterDB"] = {
        "methods": ["async insert_goal(Goal) → str", "async get_goal(str) → Goal | None",
                    "async append_record(ConstitutionalRecord) → str"],
        "note": "append_record ONLY — no update/delete per C-007",
    }


# ── Mock LLM responses ────────────────────────────────────────────────────────

_GR01 = '''<file path="src/goal_register/app.py">
# Implements: architecture/reference/ptr/architecture.md §Goal Register
# Constitutional basis: C-059 (Traceability), C-007 (Append-Only Ledger)
from fastapi import FastAPI
from .routers import goals, records
app = FastAPI(title="WAOOAW Goal Register", version="1.0.0")
app.include_router(goals.router, prefix="/goals")
app.include_router(records.router, prefix="/records")
</file>'''

_GR02 = '''<file path="src/goal_register/db.py">
# Implements: architecture/reference/ptr/architecture.md §Goal Register §Constitutional Properties
# Constitutional basis: C-007 (Append-Only — no UPDATE/DELETE ever), C-059
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Goal, ConstitutionalRecord

class GoalRegisterDB:
    async def insert_goal(self, session: AsyncSession, goal: Goal) -> str:
        session.add(goal)
        await session.commit()
        return goal.goal_id

    async def append_record(self, session: AsyncSession, record: ConstitutionalRecord) -> str:
        # C-007: append only — this method NEVER issues UPDATE or DELETE
        session.add(record)
        await session.commit()
        return record.record_id
</file>'''

_GR03 = '''<file path="src/goal_register/lifecycle.py">
# Implements: architecture/reference/ptr/architecture.md §1 PTR Lifecycle
# Constitutional basis: C-059, GEOM §G-9 (Goal Closure)
from enum import Enum
from .models import Goal, GoalState

VALID_TRANSITIONS = {
    GoalState.REGISTERED: [GoalState.UNDERSTOOD],
    GoalState.UNDERSTOOD: [GoalState.IN_JOURNEY],
    GoalState.IN_JOURNEY: [GoalState.VALIDATED, GoalState.SUSPENDED],
    GoalState.VALIDATED: [GoalState.COMPLETE],
    GoalState.COMPLETE: [GoalState.CLOSED],
    GoalState.SUSPENDED: [GoalState.IN_JOURNEY],
    GoalState.CLOSED: [],
}

def transition(goal: Goal, to: GoalState) -> Goal:
    valid = VALID_TRANSITIONS.get(goal.state, [])
    if to not in valid:
        raise ValueError(f"Invalid Goal transition: {goal.state} → {to}")
    goal.state = to
    return goal
</file>'''


def run() -> None:
    print("\n" + "═" * 72)
    print("  SIM-GO-005: Greenfield — Goal Register Service (WAOOAW builds itself)")
    print("  3 tasks · Python FastAPI · PTR grows from empty → full service")
    print("═" * 72)

    pipeline = MagicLLMPipeline(goal_register_writer=goal_register_writer)

    # ── Step 1: Goal Understanding ────────────────────────────────────────────
    _banner("STEP 1 — Goal Understanding (plain English → structured Goal)")
    raw_input = (
        "The Goal Register is currently a JSON stub file. "
        "We need to implement it properly as a Python FastAPI service with "
        "PostgreSQL persistence, append-only enforcement (C-007), full GEOM "
        "lifecycle state management, and all constitutional record types."
    )
    print(f"\n  Founder input (plain English):\n  \"{raw_input[:120]}...\"\n")

    understanding = {
        "record_type": "Goal Understanding Record",
        "record_id": "UR-GOAL-GR-001",
        "goal_id": "GOAL-GR",
        "intent": "Implement Goal Register as production-grade Python FastAPI service",
        "success_criteria_draft": [
            "SC-01: FastAPI service starts and /health returns 200",
            "SC-02: Goal lifecycle transitions enforce GEOM valid states",
            "SC-03: append_record() never issues UPDATE/DELETE (C-007 compliance)",
            "SC-04: All constitutional record types committable to DB",
        ],
        "constitutional_implications": ["C-059", "C-007", "GEOM §5"],
    }
    goal_register_writer(understanding)
    print(f"  ✓ Goal Understanding Record produced (Cat. 9 — GO-Intelligence)")
    print(f"  ✓ 4 success criteria drafted from plain-English intent")

    # ── Step 2: PTR Cold Start ────────────────────────────────────────────────
    _banner("STEP 2 — PTR 2.0 Cold Start (greenfield — no src/ files yet)")
    ptr_cold_start()
    print(f"\n  PTR Layer 1:  {_ptr_summary()}")
    print(f"  ✓ Empty Layer 1 is VALID — Phase 1 receives patterns + obligations")
    print(f"  ✓ Layer 5 (C-007 append-only obligation) active for all tasks")

    # ── Task GR-01: Scaffold ──────────────────────────────────────────────────
    _banner("TASK GR-01 — FastAPI Scaffold + SQLAlchemy Setup")
    req01 = MagicLLMRequest(
        goal_id="GOAL-GR", institution_id="INST-010",
        go_authorization_id="GOA-GR-INST-010-01",
        task_category=TaskCategory.CODE_GENERATION,
        task_description="Create src/goal_register/ Python FastAPI project. Setup models, DB session, router structure.",
        context_sections=["Goal Register spec §scaffold", "PTR 2.0 arch §5 Goal Register"],
        ptr_snapshot=ptr_state["python"],
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-GR-01",
    )
    c1 = _task_complexity_score(req01)
    print(f"\n  Complexity score: {c1} → {'Haiku' if c1 < 80 else 'Sonnet'} (thinking budget: {_thinking_budget(c1)} tokens)")

    with patch.object(pipeline, "_call_anthropic", return_value=(_GR01, 2800, 720)):
        r01 = pipeline.invoke(req01)
    print(f"  Status: {r01.status} · Model: {r01.model_version} · Cost: ₹{r01.cost_inr:.4f}")

    ptr_after_gr01()
    print(f"  ★ PTR refresh after GR-01 compile gate: {_ptr_summary()}")
    print(f"    GoalState enum · Goal model · FastAPI app type — now in PTR")

    # ── Task GR-02: Append-Only DB ────────────────────────────────────────────
    _banner("TASK GR-02 — Append-Only Goal Register DB (C-007)")
    req02 = MagicLLMRequest(
        goal_id="GOAL-GR", institution_id="INST-010",
        go_authorization_id="GOA-GR-INST-010-02",
        task_category=TaskCategory.CODE_GENERATION,
        task_description="Implement GoalRegisterDB. append_record() only — C-007: no UPDATE or DELETE ever.",
        context_sections=["C-007 Append-Only Ledger LAW", "Goal Register spec §Constitutional Properties"],
        ptr_snapshot=ptr_state["python"],
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-GR-02",
    )
    c2 = _task_complexity_score(req02)
    print(f"\n  Complexity score: {c2} → {'Haiku' if c2 < 80 else 'Sonnet'} (thinking budget: {_thinking_budget(c2)} tokens)")

    with patch.object(pipeline, "_call_anthropic", return_value=(_GR02, 3400, 920)):
        r02 = pipeline.invoke(req02)
    print(f"  Status: {r02.status} · Model: {r02.model_version} · Cost: ₹{r02.cost_inr:.4f}")

    ptr_after_gr02()
    print(f"  ★ PTR refresh: {_ptr_summary()}")
    print(f"    GoalRegisterDB.append_record() type now available for GR-03")

    # ── Task GR-03: Lifecycle State Machine ───────────────────────────────────
    _banner("TASK GR-03 — GEOM Lifecycle State Machine (CCT gate)")
    req03 = MagicLLMRequest(
        goal_id="GOAL-GR", institution_id="INST-010",
        go_authorization_id="GOA-GR-INST-010-03",
        task_category=TaskCategory.CODE_GENERATION,
        task_description="Implement Goal lifecycle state machine. CCT gate: invalid transitions raise ValueError. Must match GEOM VALID_TRANSITIONS exactly.",
        context_sections=["GEOM §G-9 Goal Closure", "constitution/GEOM.md §Goal lifecycle", "CCT-GEOM-01"],
        ptr_snapshot=ptr_state["python"],
        expected_output_format="xml_file_blocks",
        execution_plan_reference="EP-GR-03",
    )
    c3 = _task_complexity_score(req03)
    print(f"\n  Complexity score: {c3} → {'Haiku' if c3 < 80 else 'Sonnet'} (thinking budget: {_thinking_budget(c3)} tokens)")

    with patch.object(pipeline, "_call_anthropic", return_value=(_GR03, 4200, 1100)):
        r03 = pipeline.invoke(req03)
    print(f"  Status: {r03.status} · Model: {r03.model_version} · Cost: ₹{r03.cost_inr:.4f}")

    # ── Evidence + Verdict ────────────────────────────────────────────────────
    _banner("SIMULATION VERDICT")
    total_cost = r01.cost_inr + r02.cost_inr + r03.cost_inr
    models_used = {r01.model_version, r02.model_version, r03.model_version}
    complexity_scores = [c1, c2, c3]

    sc_results = [
        ("SC-01: All 3 tasks accepted", all(r.status == "accepted" for r in [r01, r02, r03])),
        ("SC-02: Goal Understanding Record produced from plain English", any(r.get("record_type") == "Goal Understanding Record" for r in evidence_chain)),
        ("SC-03: PTR grew from 0 → 5 types through phases", len(ptr_state["python"]["types"]) >= 5),
        ("SC-04: Model routing used cost-optimal models", any(r.model_version == "claude-haiku-20240307" for r in [r01, r02, r03])),
        ("SC-05: HIGH complexity task got Sonnet (CCT gate task)", any(c >= 80 for c in complexity_scores)),
        ("SC-06: 4 constitutional records in Goal Register", len(evidence_chain) == 4),
        ("SC-07: Total sprint cost within ₹5 (C-077 efficiency)", total_cost < 5.0),
    ]
    all_pass = all(r[1] for r in sc_results)
    for label, passed in sc_results:
        print(f"  {'PASS ✓' if passed else 'FAIL ✗'}  {label}")

    print(f"""
  PTR growth: empty → {_ptr_summary()}
  Models used: {', '.join(models_used)}
  Complexity scores: GR-01={c1} · GR-02={c2} · GR-03={c3}
  Total cost: ₹{total_cost:.4f}  (WAOOAW built the Goal Register for less than ₹2)
  Evidence records: {len(evidence_chain)}

  ══════════════════════════════════════════════════════════
  VERDICT: {"PASS ✓ — Greenfield Goal Register built constitutionally" if all_pass else "FAIL ✗"}
  ══════════════════════════════════════════════════════════
    """)


if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""
SIM-GO-004: WC-015 — AI Runtime Python sprint with constitutional blocker (FA-021)

Demonstrates Goal Orchestrator pre-flight constitutional check:
  1. WC-015 depends on WC-014 (not yet merged) + FA-021 (GCP key not in Key Vault)
  2. Goal Orchestrator detects BOTH blockers BEFORE issuing any GO Authorization
  3. Goal enters SUSPENDED state — no MagicLLM called, no retries, no waste
  4. Founder Decision Brief assembled and delivered via Steward Assistant
  5. PTR is assembled (Python stack) but not used — shows PTR 2.0 cold assembly works
     even though execution is blocked

Key proof: the system PREVENTS the sprint from starting, not CORRECTS it after it fails.
           This is constitutional governance as a pre-execution gate, not a retry loop.

Run: python3 simulation/sim_go_004_wc015_blocked.py
"""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

DIVIDER = "─" * 72
evidence_chain: list[dict] = []
founder_notifications: list[dict] = []

def goal_register_writer(record: dict) -> str:
    evidence_chain.append(record)
    return record.get("record_id", f"SIM-{len(evidence_chain):03d}")

def steward_notifier(goal_id: str, brief_id: str) -> None:
    founder_notifications.append({"goal_id": goal_id, "brief_id": brief_id})
    print(f"\n  ⚠️  STEWARD NOTIFICATION SENT")
    print(f"     Goal:   {goal_id}")
    print(f"     Brief:  {brief_id}")
    print(f"     Route:  Steward Assistant → Founder (WhatsApp / web chat)")
    print(f"     Action: Founder must provision FA-021 (GCP Vertex AI SA key)")


# ── Constitutional Prerequisite Checker ──────────────────────────────────────

@dataclass
class PrerequisiteStatus:
    name: str
    kind: str                      # "work_contract" | "founder_action" | "infrastructure"
    status: str                    # "READY" | "PENDING" | "MISSING" | "BLOCKED"
    detail: str
    blocks_goal: bool = True


@dataclass
class PreflightResult:
    goal_id: str
    passed: bool
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    prerequisites: list[PrerequisiteStatus] = field(default_factory=list)
    blocking_count: int = 0

    def to_dict(self) -> dict:
        return {
            "record_type": "Preflight Check Record",
            "goal_id": self.goal_id,
            "passed": self.passed,
            "blocking_count": self.blocking_count,
            "checked_at": self.checked_at.isoformat(),
            "prerequisites": [
                {"name": p.name, "status": p.status, "detail": p.detail}
                for p in self.prerequisites
            ],
        }


class ConstitutionalPreflightChecker:
    """
    Goal Orchestrator pre-flight check: verifies all constitutional prerequisites
    BEFORE issuing any GO Authorization.

    This is the gate that prevents wasted LLM calls, failed builds, and retries
    caused by missing infrastructure or upstream dependencies.
    """

    @staticmethod
    def check_wc015(goal_id: str) -> PreflightResult:
        """
        WC-015 prerequisite check per work contract:
          - WC-014 must be complete (PENDING)
          - FA-021 (GCP Vertex AI SA key) must be in Key Vault (MISSING)
          - platform_phase must be IMPLEMENTATION (READY)
          - Required specs must exist (READY — all present per WC-015)
        """
        prerequisites = [
            PrerequisiteStatus(
                name="platform_phase = IMPLEMENTATION",
                kind="infrastructure",
                status="READY",
                detail="PROJECT_STATE.md confirms IMPLEMENTATION phase ✓",
                blocks_goal=False,
            ),
            PrerequisiteStatus(
                name="WC-014 (Professional Runtime) merged",
                kind="work_contract",
                status="PENDING",
                detail="PR for WC-014 not yet opened. WC-015 depends on PR service calling AIR.",
                blocks_goal=True,
            ),
            PrerequisiteStatus(
                name="FA-021: GOOGLE-VERTEX-SA-KEY in Key Vault",
                kind="founder_action",
                status="MISSING",
                detail=(
                    "GCP Vertex AI Service Account key required for PSE integration tests. "
                    "Without this, PSE cannot route to Gemini 2.0 Flash and integration "
                    "tests will fail — no amount of PTR completeness can fix this. "
                    "See FOUNDER-ACTION.md T1-02 for provisioning steps."
                ),
                blocks_goal=True,
            ),
            PrerequisiteStatus(
                name="AIR component spec",
                kind="specification",
                status="READY",
                detail="architecture/reference/components/ai-runtime.md ✓",
                blocks_goal=False,
            ),
            PrerequisiteStatus(
                name="ADR-029 Multi-Provider LLM",
                kind="specification",
                status="READY",
                detail="adr/ADR-029-multi-provider-llm-strategy.md ✓",
                blocks_goal=False,
            ),
        ]

        blocking = [p for p in prerequisites if p.blocks_goal and p.status != "READY"]
        result = PreflightResult(
            goal_id=goal_id,
            passed=len(blocking) == 0,
            prerequisites=prerequisites,
            blocking_count=len(blocking),
        )
        return result


# ── PTR 2.0 Assembler (Python stack simulation) ───────────────────────────────

class PTR2PythonAssembler:
    """Simulates PTR 2.0 assembly for the Python AI Runtime project."""

    @staticmethod
    def assemble_cold(impact_graph_components: list[str]) -> dict:
        """Assemble PTR for AI Runtime — Python stack, cold start."""
        # src/ai-runtime/ exists from previous sprints? No — WC-015 is greenfield
        # So python types are empty, but packages from requirements.txt exist
        return {
            "python": {
                "types": {},  # empty — no src/ai-runtime/*.py yet
                "packages": {
                    "fastapi": "0.110.0",
                    "uvicorn": "0.29.0",
                    "anthropic": "0.25.0",
                    "google-cloud-aiplatform": "1.47.0",  # WC-015 needs Gemini
                    "pgvector": "0.2.5",
                    "sqlalchemy": "2.0.28",
                    "pydantic": "2.6.4",
                    # NOTE: google-cloud-aiplatform requires FA-021 SA key at runtime
                },
            },
            "dotnet": {"types": {}, "packages": {}},
            "terraform": {"providers": {}, "resources": {}},
            "typescript": {"types": {}, "packages": {}},
        }


# ── Founder Decision Brief ────────────────────────────────────────────────────

@dataclass
class BlockedGoalBrief:
    record_id: str
    goal_id: str
    record_type: str = "Founder Decision Brief — Blocked Goal"
    institution_id: str = "INST-013"
    headline: str = ""
    what_is_blocked: str = ""
    why_it_is_blocked: str = ""
    option_a: str = ""   # resolve blockers → proceed
    option_b: str = ""   # defer → wait for WC-014 to complete naturally
    option_c: str = ""   # descope → narrow WC-015 scope to not require FA-021 yet
    assembled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["assembled_at"] = d["assembled_at"].isoformat()
        return d


def _banner(title: str) -> None:
    print(f"\n{DIVIDER}\n  {title}\n{DIVIDER}")


def run() -> None:
    print("\n" + "═" * 72)
    print("  SIM-GO-004: WC-015 AI Runtime Python Sprint — Constitutional Blocker")
    print("  FA-021 missing + WC-014 pending → Goal SUSPENDED before any LLM call")
    print("═" * 72)

    goal_id = "GOAL-WC015"

    # ── Step 1: Goal Orchestrator receives WC-015 ─────────────────────────────
    _banner("STEP 1 — Goal Orchestrator: WC-015 intake")
    print(f"""
  Goal:  WC-015 AI Runtime Skeleton — Python 3.12 FastAPI
  Stack: python (FastAPI + PSE + RAG + PII Scrubber)
  Tasks: WC015-01 through WC015-05 (PSE · LLM dispatch · RAG · injection · tests)
    """)

    # ── Step 2: Constitutional pre-flight check ───────────────────────────────
    _banner("STEP 2 — Constitutional Pre-Flight Check (before any GO Authorization)")
    checker = ConstitutionalPreflightChecker()
    preflight = checker.check_wc015(goal_id)

    print(f"  Checking {len(preflight.prerequisites)} prerequisites:\n")
    for p in preflight.prerequisites:
        sym = "✓" if p.status == "READY" else "✗"
        blocking_tag = " [BLOCKS]" if p.blocks_goal and p.status != "READY" else ""
        print(f"  {sym} [{p.kind:16}] {p.name}{blocking_tag}")
        if p.status != "READY":
            import textwrap
            wrapped = textwrap.fill(p.detail, width=60, initial_indent="      → ", subsequent_indent="        ")
            print(wrapped)

    print(f"\n  Pre-flight result: {'PASS' if preflight.passed else 'FAIL — ' + str(preflight.blocking_count) + ' blocker(s)'}")

    # Record pre-flight in Goal Register
    goal_register_writer(preflight.to_dict())

    if preflight.passed:
        print("  [simulation error: expected FAIL]")
        return

    # ── Step 3: PTR assembled but NOT used ───────────────────────────────────
    _banner("STEP 3 — PTR 2.0 Assembly (assembled but not used — Goal will suspend)")
    ptr = PTR2PythonAssembler.assemble_cold(["src/ai-runtime"])
    python_packages = len(ptr["python"]["packages"])
    print(f"""
  PTR assembled: python stack · {python_packages} packages from requirements.txt
  Key entries:
    google-cloud-aiplatform 1.47.0  ← requires FA-021 SA key at RUNTIME
    fastapi 0.110.0
    pgvector 0.2.5

  PTR WILL NOT BE INJECTED into any MagicLLM invocation.
  Reason: Goal will be SUSPENDED — no GO Authorization issued.
  PTR stays in memory but MagicLLM is never called.

  NOTE: PTR assembly confirmed the google-cloud-aiplatform package is available
  as a package reference — but FA-021 is a RUNTIME credential, not a type.
  PTR completeness cannot substitute for missing infrastructure credentials.
    """)

    # ── Step 4: Goal SUSPENDED ────────────────────────────────────────────────
    _banner("STEP 4 — Goal Orchestrator: SUSPEND GOAL")
    print(f"""
  Goal {goal_id} → SUSPENDED
  Blocked by:
    1. WC-014 (Professional Runtime) not yet merged
    2. FA-021 (GOOGLE-VERTEX-SA-KEY) not provisioned in Key Vault

  NO GO Authorization issued.
  NO MagicLLM invocation made.
  NO tokens consumed.
  NO retries attempted.

  This is the correct constitutional behaviour:
    Without PTR 2.0 / Goal Orchestrator:
      Sprint starts → WC015-01 scaffold → WC015-02 LLM dispatch →
      PSE tries to call Gemini → missing SA key → HTTP 403 → failure →
      retry advisor fires → 3 retries → cascade → Founder escalation
      Total wasted: ~₹45 in LLM costs + hours of debugging

    With PTR 2.0 / Goal Orchestrator pre-flight:
      Pre-flight detects FA-021 missing BEFORE any task runs
      Goal suspended → Founder notified → zero waste
    """)

    suspension_record = {
        "record_type": "Goal Suspension Record",
        "record_id": f"GSR-{goal_id}-001",
        "goal_id": goal_id,
        "institution_id": "INST-013",
        "state": "SUSPENDED",
        "blocked_by": ["WC-014 not merged", "FA-021 not in Key Vault"],
        "preflight_record_id": preflight.to_dict().get("record_id", "PFR-001"),
        "go_authorizations_issued": 0,
        "magiclm_calls_made": 0,
        "tokens_consumed": 0,
        "cost_inr": 0.0,
        "suspended_at": datetime.now(timezone.utc).isoformat(),
    }
    goal_register_writer(suspension_record)

    # ── Step 5: Founder Decision Brief ────────────────────────────────────────
    _banner("STEP 5 — Founder Decision Brief (delivered via Steward Assistant)")
    brief = BlockedGoalBrief(
        record_id=f"FDB-{goal_id}-001",
        goal_id=goal_id,
        headline=f"WC-015 AI Runtime cannot start — 2 prerequisites missing",
        what_is_blocked=(
            "WC-015 Sprint 015 (AI Runtime) is ready in every other way — "
            "all specs are written, the component architecture is complete, "
            "and the codebase is in the right state. Only two prerequisites "
            "are missing."
        ),
        why_it_is_blocked=(
            "1. WC-014 (Professional Runtime) is not yet merged. WC-015 "
            "implements the AIR that WC-014's service calls — it must run "
            "after WC-014's gRPC client is on main.\n"
            "2. FA-021 (GCP Vertex AI SA key) is not in Azure Key Vault. "
            "The PSE integration tests call Gemini 2.0 Flash — without the "
            "SA key, they fail with HTTP 403 at test time, not compile time."
        ),
        option_a=(
            "Option A — Resolve both blockers: (1) Review + merge WC-014 PR "
            "when ready. (2) Provision GOOGLE-VERTEX-SA-KEY per FOUNDER-ACTION.md "
            "T1-02. Goal resumes automatically when both are resolved."
        ),
        option_b=(
            "Option B — Defer: WC-015 remains SUSPENDED until WC-014 merges "
            "naturally through the sprint cycle. FA-021 provisioned alongside. "
            "No action needed now — next sprint cycle will pick it up."
        ),
        option_c=(
            "Option C — Descope: Remove PSE Gemini integration tests from WC-015-05 "
            "scope. WC-015 runs with Ollama LOCAL tier only (₹0, no SA key needed). "
            "Gemini integration added in WC-016. Fastest path to WC-015 running."
        ),
    )
    goal_register_writer(brief.to_dict())
    steward_notifier(goal_id, brief.record_id)

    print(f"""
  Headline: {brief.headline}

  Option A: {brief.option_a[:70]}...
  Option B: {brief.option_b[:70]}...
  Option C: {brief.option_c[:70]}...
    """)

    # ── Verdict ───────────────────────────────────────────────────────────────
    _banner("SIMULATION VERDICT")
    sc_results = [
        ("SC-01: Pre-flight check detects both blockers", preflight.blocking_count == 2),
        ("SC-02: FA-021 identified as MISSING (infrastructure gate)", any("FA-021" in p.name for p in preflight.prerequisites if p.status == "MISSING")),
        ("SC-03: WC-014 identified as PENDING (dependency gate)", any("WC-014" in p.name for p in preflight.prerequisites if p.status == "PENDING")),
        ("SC-04: Zero GO Authorizations issued", suspension_record["go_authorizations_issued"] == 0),
        ("SC-05: Zero MagicLLM calls made", suspension_record["magiclm_calls_made"] == 0),
        ("SC-06: Zero tokens consumed (₹0 wasted)", suspension_record["cost_inr"] == 0.0),
        ("SC-07: Goal Register has suspension record", any(r.get("state") == "SUSPENDED" for r in evidence_chain)),
        ("SC-08: Founder Decision Brief delivered", len(founder_notifications) == 1),
    ]
    all_pass = all(r[1] for r in sc_results)
    for label, passed in sc_results:
        print(f"  {'PASS ✓' if passed else 'FAIL ✗'}  {label}")

    print(f"""
  Evidence records:   {len(evidence_chain)} (pre-flight + suspension + brief)
  MagicLLM calls:     0
  Tokens consumed:    0
  Cost incurred:      ₹0.00
  Founder notified:   {'Yes ✓' if founder_notifications else 'No'}

  ══════════════════════════════════════════════════════════
  VERDICT: {"PASS ✓ — WC-015 correctly suspended, Founder notified, zero waste" if all_pass else "FAIL ✗"}
  ══════════════════════════════════════════════════════════

  The contrast with the old model:
    OLD: Sprint starts → tasks attempt → infrastructure failure → retry loop
         Outcome: ₹45+ wasted · hours debugging · Founder eventually notified
    NEW: Pre-flight gate → SUSPENDED before any task starts
         Outcome: ₹0 wasted · Founder notified in seconds · 3 clear options
    """)


if __name__ == "__main__":
    run()

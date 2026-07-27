# Implements: architecture/reference/goal-orchestrator/component-contracts.md §3 §4
# Constitutional basis: C-076 (≥90% test coverage), C-086 (Pre-Execution Simulation Gate)
"""
SIM-GO-001: End-to-end Goal execution simulation.

Covers GOAL-002 SC-07:
  raw Goal → AI understanding → routing → EEM → gate fail → cascade →
  L1 exhausted → L2 skip (Phase 1) → L3 skip → Founder escalation → decision

No real LLM calls — _call_anthropic is patched to return controlled responses.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_file_response(path: str = "src/test/File.cs", content: str = "// test") -> str:
    """Returns a valid XML file block response with constitutional annotations."""
    return (
        f'<file path="{path}">\n'
        f'# Implements: architecture/reference/test.md §Test\n'
        f'# Constitutional basis: C-059 (Traceability)\n'
        f'{content}\n'
        f'</file>'
    )

def _make_json_response(data: dict) -> str:
    return json.dumps(data)

_RECORDS_WRITTEN: list[dict] = []

def _mock_writer(record: dict) -> str:
    _RECORDS_WRITTEN.append(record)
    return record.get("record_id", f"mock-{len(_RECORDS_WRITTEN)}")


# ══════════════════════════════════════════════════════════════════════════════
# SUITE 1 — MagicLLM types
# ══════════════════════════════════════════════════════════════════════════════

class TestMagicLLMTypes:
    def test_task_category_engineering_flag(self):
        from scripts.magic_llm.types import TaskCategory
        assert TaskCategory.CODE_GENERATION.is_engineering
        assert not TaskCategory.GOAL_UNDERSTANDING.is_engineering

    def test_task_category_orchestration_flag(self):
        from scripts.magic_llm.types import TaskCategory
        assert TaskCategory.ROUTING_INTELLIGENCE.is_orchestration
        assert not TaskCategory.CODE_GENERATION.is_orchestration

    def test_decision_record_to_dict_serialisable(self):
        from scripts.magic_llm.types import MagicLLMDecisionRecord, TaskCategory
        rec = MagicLLMDecisionRecord(
            institution_id="INST-008",
            invoked_by="INST-010",
            goal_id="GOAL-TEST",
            record_id="MDR-GOAL-TEST-001",
            task_category=TaskCategory.CODE_GENERATION,
        )
        d = rec.to_dict()
        assert d["task_category"] == "CODE_GENERATION"
        assert "produced_at" in d
        # Must be JSON-serialisable
        json.dumps(d, default=str)

    def test_magic_llm_request_fields(self):
        from scripts.magic_llm.types import MagicLLMRequest, TaskCategory
        req = MagicLLMRequest(
            goal_id="GOAL-001",
            institution_id="INST-010",
            go_authorization_id="GOA-001",
            task_category=TaskCategory.CODE_GENERATION,
            task_description="test",
            context_sections=["section1"],
            ptr_snapshot={},
            expected_output_format="xml_file_blocks",
            execution_plan_reference="EP-001",
        )
        assert req.goal_id == "GOAL-001"
        assert req.cascade_level is None


# ══════════════════════════════════════════════════════════════════════════════
# SUITE 2 — MagicLLM Pipeline
# ══════════════════════════════════════════════════════════════════════════════

class TestMagicLLMPipeline:

    def _make_pipeline(self):
        from scripts.magic_llm.pipeline import MagicLLMPipeline
        _RECORDS_WRITTEN.clear()
        return MagicLLMPipeline(goal_register_writer=_mock_writer)

    def _make_code_request(self, **kw):
        from scripts.magic_llm.types import MagicLLMRequest, TaskCategory
        return MagicLLMRequest(
            goal_id=kw.get("goal_id", "GOAL-SIM"),
            institution_id="INST-010",
            go_authorization_id="GOA-SIM",
            task_category=TaskCategory.CODE_GENERATION,
            task_description="Generate test file",
            context_sections=["spec content"],
            ptr_snapshot={"MyClass": "namespace Waooaw"},
            expected_output_format="xml_file_blocks",
            execution_plan_reference="EP-SIM",
        )

    # AC-01: accepted response produces Decision Record (Evidence First)
    def test_happy_path_records_decision_before_returning(self):
        pipeline = self._make_pipeline()
        request = self._make_code_request()
        good_response = (_make_file_response(), 1234, 4567)

        with patch.object(pipeline, "_call_anthropic", return_value=good_response):
            response = pipeline.invoke(request)

        assert response.status == "accepted"
        # Decision Record must be committed (Evidence First — C-059)
        decision_records = [r for r in _RECORDS_WRITTEN if r.get("record_type") == "MagicLLM Decision Record"]
        assert len(decision_records) == 1
        dr = decision_records[0]
        assert dr["goal_id"] == "GOAL-SIM"
        assert dr["invoked_by"] == "INST-010"
        assert dr["institution_id"] == "INST-008"

    # AC-02: format gate rejects response with no <file> blocks
    def test_format_gate_rejects_missing_file_blocks(self):
        pipeline = self._make_pipeline()
        request = self._make_code_request()

        with patch.object(pipeline, "_call_anthropic", return_value=("just some prose", 100, 200)):
            response = pipeline.invoke(request)

        assert response.status == "retry_needed"
        from scripts.magic_llm.types import FailureClassification
        assert response.failure_classification == FailureClassification.FORMAT_FAILURE

    # AC-03: annotation gate rejects response missing # Implements: header
    def test_annotation_gate_rejects_missing_header(self):
        pipeline = self._make_pipeline()
        request = self._make_code_request()
        no_header = '<file path="src/Test.cs">\npublic class Test {}\n</file>'

        with patch.object(pipeline, "_call_anthropic", return_value=(no_header, 100, 200)):
            response = pipeline.invoke(request)

        assert response.status == "retry_needed"
        from scripts.magic_llm.types import FailureClassification
        assert response.failure_classification == FailureClassification.ANNOTATION_MISSING

    # AC-04: Cat. 7-13 (Gemini) — route to Gemini, graceful no-key fallback (ADR-033)
    def test_gemini_cat_routes_to_gemini_model(self):
        """ADR-033: Cat. 7-13 use gemini-2.0-flash, not Anthropic."""
        from scripts.magic_llm.types import MagicLLMRequest, TaskCategory
        from scripts.magic_llm.pipeline import _GEMINI_FLASH
        pipeline = self._make_pipeline()
        req = MagicLLMRequest(
            goal_id="GOAL-SIM",
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.GOAL_UNDERSTANDING,
            task_description="Parse this goal: implement tenant isolation",
            context_sections=["raw input"],
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        )
        # Mock _call_gemini so no real network call needed
        with patch.object(pipeline, "_call_gemini", return_value=('{"goal_id": "G-001"}', 100, 50)) as mock_gemini:
            response = pipeline.invoke(req)
        mock_gemini.assert_called_once()
        assert response.model_version == _GEMINI_FLASH
        assert response.model_provider == "google"

    # AC-04b: Cat. 7-13 — no annotation gate applied (ADR-033)
    def test_gemini_cat_no_annotation_gate(self):
        """ADR-033: Cat. 7-13 produce prose/JSON, annotation gate must NOT fire."""
        from scripts.magic_llm.types import MagicLLMRequest, TaskCategory
        pipeline = self._make_pipeline()
        req = MagicLLMRequest(
            goal_id="GOAL-SIM",
            institution_id="INST-013",
            go_authorization_id="internal",
            task_category=TaskCategory.ROUTING_INTELLIGENCE,
            task_description="Route this Goal to the correct institution",
            context_sections=["goal context"],
            ptr_snapshot={},
            expected_output_format="json",
            execution_plan_reference="",
        )
        # Response has no "# Implements:" — must still pass (no annotation gate for Cat. 7-13)
        plain_json = '{"institution": "INST-010", "wc": "WC-013"}'
        with patch.object(pipeline, "_call_gemini", return_value=(plain_json, 80, 30)):
            response = pipeline.invoke(req)
        assert response.status == "accepted"
        assert "ANNOTATION" not in response.gates_evaluated

    # AC-05: retry_with_enhanced_context injects correction and re-invokes
    def test_retry_with_enhanced_context(self):
        pipeline = self._make_pipeline()
        request = self._make_code_request()
        good_response = (_make_file_response(), 100, 200)
        failure_evidence = {"failure_classification": "FORMAT_FAILURE"}

        with patch.object(pipeline, "_call_anthropic", return_value=(_make_file_response(), 100, 200)):
            response = pipeline.retry_with_enhanced_context(
                goal_id="GOAL-SIM",
                failure_evidence=failure_evidence,
                attempt=1,
                original_request=request,
            )

        assert response.status == "accepted"

    # AC-06: cost estimation returns a float
    def test_cost_estimation(self):
        pipeline = self._make_pipeline()
        cost = pipeline._estimate_cost("claude-sonnet-4-6", 1000, 500)
        assert isinstance(cost, float)
        assert cost > 0


# ══════════════════════════════════════════════════════════════════════════════
# SUITE 3 — CascadeHandler state machine
# ══════════════════════════════════════════════════════════════════════════════

class TestCascadeHandler:

    def _make_handler(self, l1_max=1, l2_max=1, l3_max=1):
        from scripts.goal_orchestrator.cascade_handler import (
            CascadeContext, CascadeHandler, CascadeState,
        )
        from scripts.magic_llm.pipeline import MagicLLMPipeline
        from scripts.goal_orchestrator.intelligence import GOIntelligence

        _RECORDS_WRITTEN.clear()
        ctx = CascadeContext(
            goal_id="GOAL-CASCADE-TEST",
            gate_step=10,
            l1_max=l1_max,
            l2_max=l2_max,
            l3_max=l3_max,
        )
        pipeline = MagicLLMPipeline(goal_register_writer=_mock_writer)
        go = GOIntelligence(pipeline, _mock_writer)
        handler = CascadeHandler(
            context=ctx,
            goal_register_writer=_mock_writer,
            magic_llm=pipeline,
            go_intelligence=go,
        )
        return handler, ctx, CascadeState

    def _make_request(self):
        from scripts.magic_llm.types import MagicLLMRequest, TaskCategory
        return MagicLLMRequest(
            goal_id="GOAL-CASCADE-TEST",
            institution_id="INST-010",
            go_authorization_id="GOA-CASCADE",
            task_category=TaskCategory.CODE_GENERATION,
            task_description="test task",
            context_sections=["spec"],
            ptr_snapshot={},
            expected_output_format="xml_file_blocks",
            execution_plan_reference="EP-001",
        )

    # AC-07: NOMINAL → L1_ACTIVE is the only valid first transition
    def test_initial_state_is_nominal(self):
        _, ctx, CascadeState = self._make_handler()
        assert ctx.state == CascadeState.NOMINAL

    # AC-08: invalid transition raises ValueError
    def test_invalid_transition_raises(self):
        from scripts.goal_orchestrator.cascade_handler import CascadeState
        handler, ctx, _ = self._make_handler()
        ctx.state = CascadeState.NOMINAL
        with pytest.raises(ValueError, match="Invalid cascade transition"):
            handler._transition(CascadeState.RESOLVED)  # NOMINAL cannot go directly to RESOLVED

    # AC-09: L1 resolves if pipeline accepts on first attempt
    def test_l1_resolves_on_first_success(self):
        handler, ctx, CascadeState = self._make_handler(l1_max=3)
        handler.set_original_request(self._make_request())
        good = (_make_file_response(), 100, 200)
        failure_evidence = {"failure_classification": "FORMAT_FAILURE"}

        with patch.object(handler._llm, "_call_anthropic", return_value=good):
            final_state = handler.on_gate_fail(failure_evidence)

        assert final_state == CascadeState.RESOLVED
        assert ctx.resolved_by_level == 1
        assert ctx.l1_attempts == 1

    # AC-10: full cascade (L1 fail → L2 skip → L3 skip → FOUNDER_PENDING)
    def test_full_cascade_reaches_founder_pending(self):
        handler, ctx, CascadeState = self._make_handler(l1_max=1, l2_max=1, l3_max=1)
        handler.set_original_request(self._make_request())
        # Always return a bad response (no <file> blocks, no annotation)
        bad = ("no files here", 100, 200)
        failure_evidence = {"failure_classification": "FORMAT_FAILURE", "failure_detail": "no files"}

        notified: list[tuple] = []
        handler._notify = lambda g, b: notified.append((g, b))

        with patch.object(handler._llm, "_call_anthropic", return_value=bad):
            final_state = handler.on_gate_fail(failure_evidence)

        assert final_state == CascadeState.FOUNDER_PENDING
        # Founder must have been notified
        assert len(notified) == 1
        assert notified[0][0] == "GOAL-CASCADE-TEST"

    # AC-11: on_founder_decision accepts a/b/c and transitions to ESCALATED
    def test_founder_decision_transitions_to_escalated(self):
        handler, ctx, CascadeState = self._make_handler(l1_max=1)
        handler.set_original_request(self._make_request())
        bad = ("no files", 100, 200)
        handler._notify = lambda g, b: None

        with patch.object(handler._llm, "_call_anthropic", return_value=bad):
            handler.on_gate_fail({"failure_classification": "FORMAT_FAILURE"})

        assert ctx.state == CascadeState.FOUNDER_PENDING
        handler.on_founder_decision("b")
        assert ctx.state == CascadeState.ESCALATED
        assert ctx.founder_decision == "b"

    # AC-12: on_founder_decision rejects invalid options
    def test_founder_decision_rejects_invalid(self):
        handler, ctx, CascadeState = self._make_handler(l1_max=1)
        ctx.state = CascadeState.FOUNDER_PENDING
        with pytest.raises(ValueError, match="must be a, b, or c"):
            handler.on_founder_decision("x")

    # AC-13: L1 attempt records are written per attempt
    def test_l1_attempt_records_written(self):
        handler, ctx, CascadeState = self._make_handler(l1_max=3)
        handler.set_original_request(self._make_request())
        bad = ("no files", 100, 200)
        handler._notify = lambda g, b: None

        with patch.object(handler._llm, "_call_anthropic", return_value=bad):
            handler.on_gate_fail({"failure_classification": "FORMAT_FAILURE"})

        l1_records = [r for r in _RECORDS_WRITTEN if r.get("record_type") == "L1 Attempt Record"]
        assert len(l1_records) == 3  # one per attempt
        assert all(r["goal_id"] == "GOAL-CASCADE-TEST" for r in l1_records)


# ══════════════════════════════════════════════════════════════════════════════
# SUITE 4 — GOIntelligence
# ══════════════════════════════════════════════════════════════════════════════

class TestGOIntelligence:

    def _make_go(self):
        from scripts.magic_llm.pipeline import MagicLLMPipeline
        from scripts.goal_orchestrator.intelligence import GOIntelligence
        _RECORDS_WRITTEN.clear()
        pipeline = MagicLLMPipeline(goal_register_writer=_mock_writer)
        go = GOIntelligence(pipeline, _mock_writer)
        return go, pipeline

    # AC-14: understand_goal returns record with Evidence First
    def test_understand_goal_records_evidence(self):
        go, pipeline = self._make_go()
        from scripts.magic_llm.orchestration import GoalUnderstandingRequest
        req = GoalUnderstandingRequest(
            raw_input="I want an agent that tracks my portfolio performance",
            registrant_id="founder",
        )
        understanding_json = _make_json_response({
            "intent": "Track portfolio performance with constitutional governance",
            "success_criteria_draft": [{"id": "SC-01", "criterion": "Portfolio tracked"}],
            "constitutional_implications": ["C-059"],
            "clarification_needed": False,
            "clarifications": [],
            "related_goals": [],
        })

        with patch.object(pipeline, "_call_anthropic", return_value=(understanding_json, 100, 200)):
            record = go.understand_goal(req)

        assert record.intent != ""
        # Evidence First — record committed before return
        understanding_records = [r for r in _RECORDS_WRITTEN if r.get("record_type") == "Goal Understanding Record"]
        assert len(understanding_records) == 1
        assert understanding_records[0]["institution_id"] == "INST-013"

    # AC-15: plan_routing returns RoutingDecisionRecord with Evidence First
    def test_plan_routing_records_evidence(self):
        go, pipeline = self._make_go()
        from scripts.magic_llm.orchestration import RoutingRequest
        req = RoutingRequest(
            goal_id="GOAL-ROUTE-TEST",
            goal_classification={"nature": "Build", "scope": "Narrow"},
            understanding_record_id="UR-001",
            available_institutions=[{"id": "INST-004", "scope": "architecture"}],
            performance_history=[],
            active_institution_load={},
        )
        routing_json = _make_json_response({
            "selected_institutions": ["INST-004", "INST-010"],
            "execution_sequence": "sequential",
            "routing_rationale": {"INST-004": "Architecture scope match"},
        })

        with patch.object(pipeline, "_call_anthropic", return_value=(routing_json, 100, 200)):
            record = go.plan_routing(req)

        assert "INST-004" in record.selected_institutions
        routing_records = [r for r in _RECORDS_WRITTEN if r.get("record_type") == "Routing Decision Record"]
        assert len(routing_records) == 1

    # AC-16: research_query raises NotImplementedError in Phase 1
    def test_research_query_raises_in_phase1(self):
        go, _ = self._make_go()
        with pytest.raises(NotImplementedError, match="Phase 2"):
            go.research_query("GOAL-TEST", {}, [])

    # AC-17: synthesise_decision raises NotImplementedError in Phase 1
    def test_synthesise_decision_raises_in_phase1(self):
        go, _ = self._make_go()
        with pytest.raises(NotImplementedError, match="Phase 2"):
            go.synthesise_decision("GOAL-TEST", [], None, None)


# ══════════════════════════════════════════════════════════════════════════════
# SUITE 5 — SC-07 End-to-End: Full Goal Execution Flow
# ══════════════════════════════════════════════════════════════════════════════

class TestEndToEndGoalExecution:
    """
    SC-07: raw Goal → understanding → routing → gate fail →
           cascade (L1×3 fail → L2 skip → L3 skip → Founder) →
           Founder decision → ESCALATED.

    Proves the full GEOM §10 Remediation Cascade runs constitutionally.
    """

    def test_sc07_full_goal_execution_cascade_to_founder(self):
        from scripts.magic_llm.pipeline import MagicLLMPipeline
        from scripts.magic_llm.orchestration import GoalUnderstandingRequest, RoutingRequest
        from scripts.goal_orchestrator.cascade_handler import (
            CascadeContext, CascadeHandler, CascadeState,
        )
        from scripts.goal_orchestrator.intelligence import GOIntelligence

        _RECORDS_WRITTEN.clear()
        pipeline = MagicLLMPipeline(goal_register_writer=_mock_writer)
        go = GOIntelligence(pipeline, _mock_writer)

        # ── Stage 1: raw Goal → AI Understanding (Cat. 9 via Cat. 1 proxy) ──
        raw_input = "I want to understand the business impact of migrating our payment service to async"
        understanding_json = _make_json_response({
            "intent": "Understand business impact of payment service async migration",
            "success_criteria_draft": [{"id": "SC-01", "criterion": "Impact analysis complete"}],
            "constitutional_implications": ["C-059"],
            "clarification_needed": False,
            "clarifications": [],
            "related_goals": [],
        })

        with patch.object(pipeline, "_call_anthropic", return_value=(understanding_json, 500, 300)):
            understanding = go.understand_goal(GoalUnderstandingRequest(
                raw_input=raw_input,
                registrant_id="founder",
            ))

        assert understanding.intent != ""
        assert not understanding.clarification_needed

        # ── Stage 2: AI Routing (Cat. 10 via Cat. 1 proxy) ──────────────────
        routing_json = _make_json_response({
            "selected_institutions": ["INST-004", "INST-010"],
            "execution_sequence": "sequential",
            "routing_rationale": {"INST-004": "Architecture match", "INST-010": "Implementation"},
        })

        with patch.object(pipeline, "_call_anthropic", return_value=(routing_json, 400, 200)):
            routing = go.plan_routing(RoutingRequest(
                goal_id=understanding.goal_id,
                goal_classification={"nature": "Build", "scope": "Narrow", "risk": "Medium"},
                understanding_record_id=understanding.record_id,
                available_institutions=[
                    {"id": "INST-004", "scope": "architecture"},
                    {"id": "INST-010", "scope": "implementation"},
                ],
                performance_history=[],
                active_institution_load={},
            ))

        assert len(routing.selected_institutions) >= 1

        # ── Stage 3: EEM Step 08 — Gate FAIL (simulate failure) ─────────────
        from scripts.magic_llm.types import MagicLLMRequest, TaskCategory
        step08_request = MagicLLMRequest(
            goal_id=understanding.goal_id,
            institution_id="INST-010",
            go_authorization_id="GOA-SIM-001",
            task_category=TaskCategory.CODE_GENERATION,
            task_description="Generate PaymentService async implementation",
            context_sections=["Spec: async payment service migration"],
            ptr_snapshot={"PaymentService": "namespace Waooaw.Payment"},
            expected_output_format="xml_file_blocks",
            execution_plan_reference="EP-SIM-001",
        )

        # Bad response — simulates Gate Fail scenario
        with patch.object(pipeline, "_call_anthropic", return_value=("bad output", 100, 100)):
            step08_result = pipeline.invoke(step08_request)

        assert step08_result.status == "retry_needed"  # Gate Fail detected

        # ── Stage 4: Cascade — L1 (3×fail) → L2 skip → L3 skip → Founder ───
        ctx = CascadeContext(
            goal_id=understanding.goal_id,
            gate_step=10,
            l1_max=3,
            l2_max=2,
            l3_max=1,
        )
        notified_escalations: list[tuple] = []

        handler = CascadeHandler(
            context=ctx,
            goal_register_writer=_mock_writer,
            magic_llm=pipeline,
            go_intelligence=go,
            steward_notifier=lambda g, b: notified_escalations.append((g, b)),
        )
        handler.set_original_request(step08_request)

        with patch.object(pipeline, "_call_anthropic", return_value=("bad output", 100, 100)):
            final_state = handler.on_gate_fail({
                "failure_classification": "FORMAT_FAILURE",
                "failure_detail": "no <file> blocks — Gate 10 outcome misalignment",
            })

        # FOUNDER_PENDING: cascade exhausted all levels autonomously
        assert final_state == CascadeState.FOUNDER_PENDING
        assert ctx.l1_attempts == 3          # all 3 L1 attempts exhausted
        assert len(notified_escalations) == 1  # Founder notified exactly once

        # ── Stage 5: Founder Decision ─────────────────────────────────────────
        handler.on_founder_decision("a")  # option a: scope reduction
        assert ctx.state == CascadeState.ESCALATED
        assert ctx.founder_decision == "a"

        # ── Evidence verification ─────────────────────────────────────────────
        all_types = [r.get("record_type") for r in _RECORDS_WRITTEN]

        # Every required record type must be present
        assert "MagicLLM Decision Record" in all_types    # from pipeline.invoke
        assert "Goal Understanding Record" in all_types   # from understand_goal (Evidence First)
        assert "Routing Decision Record" in all_types     # from plan_routing (Evidence First)
        assert "L1 Attempt Record" in all_types           # from cascade L1

        # Founder Evidence Package must exist
        founder_records = [r for r in _RECORDS_WRITTEN if "Founder" in r.get("record_type", "")]
        assert len(founder_records) >= 1

        print(f"\n  SC-07 PASS: {len(_RECORDS_WRITTEN)} Goal Register records produced")
        print(f"  Record types: {sorted(set(all_types))}")

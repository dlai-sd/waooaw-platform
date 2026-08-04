# constitutional_basis: C-099 (Decision Consequence Map), C-023 (Evidence First), C-073 (Annotations)
# ib_item: IB-009
# produced_by: Platform IT Expert — 2026-08-04
# gate: Runtime audit log integrity — every DETERMINISTIC_REQUIRED action must have a verification record

"""
CCT-DCM-03 — CE Proto DCM Contract + Runtime Audit Integrity

Two layers:

  CCT-DCM-03a (structural — runs now): The CE gRPC proto must include
  DcmCategory and DcmOutcome enums, and ValidateActionRequest must carry
  dcm_category. This is a structural guard that ensures the architectural
  contract for DCM enforcement exists before any agent implementation begins.

  CCT-DCM-03b (runtime — requires CE DCM evaluator implementation):
  For every DETERMINISTIC_REQUIRED action in constitutional.audit_records,
  a corresponding independent verification record must exist.
  MARKED PENDING until CE DcmEvaluator is implemented (Track 2 of C-099).

C-099 states: "An agent that proceeds past PROCEED_DETERMINISTIC without
completing independent verification is in violation of this claim at runtime.
This violation is detectable by CCT-DCM-03."

Runs on: every PR touching src/**/constitutional_service.proto
         every PR touching src/constitutional-engine/Evaluators/ (CCT-DCM-03b)
Blocking (03a): Yes — missing proto contract = CE cannot enforce C-099
Blocking (03b): Yes (once CE DcmEvaluator is implemented)
"""
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent

# Canonical proto — CE is source of truth; other copies must be in sync (CCT-PROTO-01).
CE_PROTO = REPO_ROOT / "src" / "constitutional-engine" / "Protos" / "constitutional_service.proto"
BP_PROTO = REPO_ROOT / "src" / "business-platform" / "Protos" / "constitutional_service.proto"
PR_PROTO = REPO_ROOT / "src" / "professional-runtime" / "proto" / "constitutional_service.proto"
AIR_PROTO = REPO_ROOT / "src" / "ai-runtime" / "proto" / "constitutional_service.proto"

ALL_PROTOS = [CE_PROTO, BP_PROTO, PR_PROTO, AIR_PROTO]

# ─── CCT-DCM-03a: Proto structural contract ──────────────────────────────────

@pytest.mark.parametrize("proto", ALL_PROTOS, ids=lambda p: p.parts[-3])
def test_proto_declares_dcm_category_enum(proto: Path) -> None:
    """CCT-DCM-03a-1: Every CE proto copy must declare the DcmCategory enum (C-099).

    Without this enum, CE has no type-safe way to accept and route DCM decisions.
    """
    content = proto.read_text(encoding="utf-8")
    assert "enum DcmCategory" in content, (
        f"CCT-DCM-03a-1 FAIL: {proto} does not declare 'enum DcmCategory'.\n"
        f"Add DcmCategory enum with DCM_CATEGORY_UNSPECIFIED=0, "
        f"DCM_CATEGORY_DETERMINISTIC_REQUIRED=1, DCM_CATEGORY_CONSISTENT_SUFFICIENT=2.\n"
        f"Constitutional basis: C-099 (DCM), ADR-040."
    )
    assert "DCM_CATEGORY_DETERMINISTIC_REQUIRED" in content, (
        f"CCT-DCM-03a-1 FAIL: DcmCategory enum in {proto} missing "
        f"DCM_CATEGORY_DETERMINISTIC_REQUIRED value."
    )
    assert "DCM_CATEGORY_CONSISTENT_SUFFICIENT" in content, (
        f"CCT-DCM-03a-1 FAIL: DcmCategory enum in {proto} missing "
        f"DCM_CATEGORY_CONSISTENT_SUFFICIENT value."
    )


@pytest.mark.parametrize("proto", ALL_PROTOS, ids=lambda p: p.parts[-3])
def test_proto_declares_dcm_outcome_enum(proto: Path) -> None:
    """CCT-DCM-03a-2: Every CE proto copy must declare the DcmOutcome enum (C-099).

    DcmOutcome is the CE response that tells the agent which path to take.
    Without it, agents cannot receive PROCEED_DETERMINISTIC routing.
    """
    content = proto.read_text(encoding="utf-8")
    assert "enum DcmOutcome" in content, (
        f"CCT-DCM-03a-2 FAIL: {proto} does not declare 'enum DcmOutcome'.\n"
        f"Add DcmOutcome with DCM_PROCEED_AUTONOMOUS=1, "
        f"DCM_PROCEED_DETERMINISTIC=2, DCM_BLOCKED=3.\n"
        f"Constitutional basis: C-099, ADR-040."
    )
    assert "DCM_PROCEED_AUTONOMOUS" in content
    assert "DCM_PROCEED_DETERMINISTIC" in content
    assert "DCM_BLOCKED" in content


@pytest.mark.parametrize("proto", ALL_PROTOS, ids=lambda p: p.parts[-3])
def test_validate_action_request_includes_dcm_category_field(proto: Path) -> None:
    """CCT-DCM-03a-3: ValidateActionRequest must include dcm_category field (C-099).

    Agents pass their DCM category to CE on every consequential action.
    If the field is missing, CE cannot route to the correct verification path.
    """
    content = proto.read_text(encoding="utf-8")
    assert "dcm_category" in content, (
        f"CCT-DCM-03a-3 FAIL: ValidateActionRequest in {proto} missing dcm_category field.\n"
        f"Add: optional DcmCategory dcm_category = 10;\n"
        f"Constitutional basis: C-099, C-041 (ValidateAction before every tool call)."
    )


@pytest.mark.parametrize("proto", ALL_PROTOS, ids=lambda p: p.parts[-3])
def test_validate_action_response_includes_dcm_outcome_field(proto: Path) -> None:
    """CCT-DCM-03a-4: ValidateActionResponse must include dcm_outcome field (C-099).

    CE must return the DCM routing decision to the agent.
    Without dcm_outcome, the agent cannot know whether to proceed autonomously
    or invoke independent verification.
    """
    content = proto.read_text(encoding="utf-8")
    assert "dcm_outcome" in content, (
        f"CCT-DCM-03a-4 FAIL: ValidateActionResponse in {proto} missing dcm_outcome field.\n"
        f"Add: DcmOutcome dcm_outcome = 6;\n"
        f"Constitutional basis: C-099."
    )


@pytest.mark.parametrize("proto", ALL_PROTOS, ids=lambda p: p.parts[-3])
def test_all_proto_copies_are_in_sync(proto: Path) -> None:
    """CCT-DCM-03a-5: All 4 proto copies must be byte-for-byte identical.

    CE proto is the canonical truth. BP, PR, and AIR are consumers.
    Divergence between copies causes gRPC contract mismatches at runtime.
    """
    canonical = CE_PROTO.read_bytes()
    copy = proto.read_bytes()
    assert canonical == copy, (
        f"CCT-DCM-03a-5 FAIL: {proto} has diverged from the canonical CE proto.\n"
        f"Run: cp src/constitutional-engine/Protos/constitutional_service.proto "
        f"{proto.relative_to(REPO_ROOT)}\n"
        f"Constitutional basis: C-032 (Spec/Code Drift — proto is the specification)."
    )


# ─── CCT-DCM-03b: Runtime audit integrity (pending CE DcmEvaluator) ──────────

@pytest.mark.skip(
    reason=(
        "CCT-DCM-03b: Pending CE DcmEvaluator implementation (Track 1B complete; "
        "Track 2 implementation not yet authorized). "
        "When CE DcmEvaluator is implemented: for every DETERMINISTIC_REQUIRED action "
        "in constitutional.audit_records, a verification_record_id must be present. "
        "Absence is a C-099 runtime violation. Remove this skip when "
        "src/constitutional-engine/Evaluators/DcmEvaluator.cs exists."
    )
)
def test_runtime_every_deterministic_action_has_verification_record() -> None:
    """CCT-DCM-03b: Audit log integrity — verification record required for DR actions.

    For every audit_records row where dcm_category = DETERMINISTIC_REQUIRED,
    a corresponding verification_record_id must be present (non-null).
    An absent verification_record is a C-099 runtime violation even if
    the action itself was correct.

    Implementation gate: requires CE DcmEvaluator + DB migration adding
    dcm_category + verification_record_id columns to constitutional.audit_records.
    """
    raise NotImplementedError(
        "CCT-DCM-03b body: query institutional.audit_records WHERE "
        "dcm_category = 'DETERMINISTIC_REQUIRED' AND verification_record_id IS NULL. "
        "Assert count == 0."
    )

# constitutional_basis: C-099 (Decision Consequence Map), C-070 (Constitutional DNA), C-073 (Annotations)
# ib_item: IB-009
# produced_by: Platform IT Expert — 2026-08-04
# gate: Activation Gate Section 16.1 — DCM section present in every agent spec

"""
CCT-DCM-01 — Agent Spec DCM Presence

Every WAOOAW agent spec must contain a Decision Consequence Map (Section 3.25).
An agent spec without a DCM section cannot pass Activation Gate Section 16 and
must not be activated.

C-099 states: "An agent spec without a DCM is incomplete and cannot pass the
AGENT-AUTHORING-GUIDE activation gate."

Runs on: every PR touching architecture/reference/agents/*.md
Blocking: Yes — missing DCM section = GATE BLOCKED on Activation Gate §16.1
"""
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
AGENTS_DIR = REPO_ROOT / "architecture" / "reference" / "agents"

# Every file in this list must contain a Section 3.25 DCM block.
# Exclude framework/guide files — they define the standard, they do not implement it.
EXCLUDED = {
    "AGENT-AUTHORING-GUIDE.md",
    "CONSTITUTIONAL_DNA.md",
    "AGENT-BASE-SPEC.md",
}

AGENT_SPECS = [
    f for f in AGENTS_DIR.glob("*.md")
    if f.name not in EXCLUDED
    and not f.name.startswith("AVD")
]


@pytest.mark.parametrize("spec", AGENT_SPECS, ids=lambda f: f.name)
def test_agent_spec_has_decision_consequence_map_section(spec: Path) -> None:
    """CCT-DCM-01a: Every agent spec must contain 'decision_consequence_map:'.

    Gate: AGENT-AUTHORING-GUIDE Activation Gate Section 16.1.
    Missing this section = the agent cannot be activated.
    """
    content = spec.read_text(encoding="utf-8")
    assert "decision_consequence_map:" in content, (
        f"CCT-DCM-01a FAIL: {spec.name} is missing a Decision Consequence Map.\n"
        f"Add Section 3.25 with at least one decision_type classified as\n"
        f"DETERMINISTIC_REQUIRED or CONSISTENT_SUFFICIENT.\n"
        f"Constitutional basis: C-099 — DCM is mandatory for every agent spec.\n"
        f"Activation Gate: Section 16.1 — GATE BLOCKED until DCM is present."
    )


@pytest.mark.parametrize("spec", AGENT_SPECS, ids=lambda f: f.name)
def test_agent_spec_references_c099_check(spec: Path) -> None:
    """CCT-DCM-01b: Every agent spec must carry a C-099 check in its checklist.

    Gate: AGENT-AUTHORING-GUIDE Activation Gate Section 16.5.
    C-099 check absent = the agent's constitutional review is incomplete.
    """
    content = spec.read_text(encoding="utf-8")
    assert "C-099" in content, (
        f"CCT-DCM-01b FAIL: {spec.name} has no C-099 reference.\n"
        f"Add a C-099 check to the Constitutional Checklist:\n"
        f"  - [ ] **C-099 check (Decision Consequence Map): ...**\n"
        f"Constitutional basis: C-099, C-073 (annotation obligation).\n"
        f"Activation Gate: Section 16.5 — GATE BLOCKED until C-099 check is present."
    )


@pytest.mark.parametrize("spec", AGENT_SPECS, ids=lambda f: f.name)
def test_agent_spec_has_at_least_one_decision_type(spec: Path) -> None:
    """CCT-DCM-01c: Every DCM must classify at least one decision type.

    An empty DCM with no entries is constitutionally equivalent to no DCM.
    Every agent that takes actions has at least one consequential decision type.
    """
    content = spec.read_text(encoding="utf-8")
    has_dcm = "decision_consequence_map:" in content
    if not has_dcm:
        pytest.skip("CCT-DCM-01a already fails — no DCM to check entries in")

    has_entries = "decision_type:" in content
    assert has_entries, (
        f"CCT-DCM-01c FAIL: {spec.name} has a DCM header but no decision_type entries.\n"
        f"Every agent that acts must classify at least one decision type.\n"
        f"Constitutional basis: C-099 — DCM classifies 'every consequential decision'.\n"
        f"Activation Gate: Section 16.2 — GATE BLOCKED: undeclared decisions present."
    )

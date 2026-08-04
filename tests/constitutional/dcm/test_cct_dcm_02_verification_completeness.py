# constitutional_basis: C-099 (Decision Consequence Map), C-023 (Evidence First), C-073 (Annotations)
# ib_item: IB-009
# produced_by: Platform IT Expert — 2026-08-04
# gate: Activation Gate Section 16.3 — every DETERMINISTIC_REQUIRED decision has independent verification

"""
CCT-DCM-02 — Agent Spec DCM Structural Completeness

Every DETERMINISTIC_REQUIRED decision in every agent spec must declare an
independent_verification_method. An agent that commits an irreversible action
without independent verification is in violation of C-099 and C-023 (Evidence
First).

The consequence of misclassification: if a DETERMINISTIC_REQUIRED decision
(e.g., customer_charge, trade_execution) is missing its verification method,
the agent has a gap between its spec obligation (C-099) and its runtime
behavior — and that gap is the exact failure mode DCM was designed to prevent.

Runs on: every PR touching architecture/reference/agents/*.md
Blocking: Yes — DETERMINISTIC_REQUIRED without verification = C-099 + C-023 violation
"""
import re
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
AGENTS_DIR = REPO_ROOT / "architecture" / "reference" / "agents"

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

# Regex: extracts each DCM YAML block entry (from decision_type: to the next entry or end)
# Looks for entries that are DETERMINISTIC_REQUIRED and checks for independent_verification_method
_DCM_BLOCK_RE = re.compile(
    r"decision_consequence_map:(.*?)(?=\n```|\Z)",
    re.DOTALL,
)
_DR_ENTRY_RE = re.compile(
    r"decision_type:\s*(\S+).*?category:\s*DETERMINISTIC_REQUIRED(.*?)(?=\s*-\s*decision_type:|\Z)",
    re.DOTALL,
)


def _extract_dcm_blocks(content: str) -> list[str]:
    """Return all YAML text inside decision_consequence_map: blocks."""
    blocks = []
    for m in _DCM_BLOCK_RE.finditer(content):
        blocks.append(m.group(1))
    return blocks


@pytest.mark.parametrize("spec", AGENT_SPECS, ids=lambda f: f.name)
def test_every_deterministic_required_decision_has_verification_method(spec: Path) -> None:
    """CCT-DCM-02a: Every DETERMINISTIC_REQUIRED entry must declare independent_verification_method.

    Gate: AGENT-AUTHORING-GUIDE Activation Gate Section 16.3.
    A DETERMINISTIC_REQUIRED action without a verification method is
    constitutionally indistinguishable from no verification at all.
    """
    content = spec.read_text(encoding="utf-8")
    if "decision_consequence_map:" not in content:
        pytest.skip("CCT-DCM-01a fails — no DCM to check")

    blocks = _extract_dcm_blocks(content)
    violations: list[str] = []

    for block in blocks:
        for m in _DR_ENTRY_RE.finditer(block):
            decision_type = m.group(1).strip()
            entry_body = m.group(2)
            if "independent_verification_method" not in entry_body:
                violations.append(decision_type)

    assert not violations, (
        f"CCT-DCM-02a FAIL: {spec.name} — DETERMINISTIC_REQUIRED decisions missing "
        f"independent_verification_method:\n  {violations}\n"
        f"Every irreversible/financial/constitutional decision must declare HOW it\n"
        f"will be independently verified before the action is committed.\n"
        f"Constitutional basis: C-099, C-023 (Evidence First).\n"
        f"Activation Gate: Section 16.3 — GATE BLOCKED."
    )


@pytest.mark.parametrize("spec", AGENT_SPECS, ids=lambda f: f.name)
def test_no_deterministic_required_without_constitutional_basis(spec: Path) -> None:
    """CCT-DCM-02b: Every DETERMINISTIC_REQUIRED entry must cite its constitutional_basis.

    Traceability requirement: knowing WHY a decision is irreversible is as
    important as knowing THAT it is. An undocumented constitutional_basis
    cannot be reviewed, tested, or disputed.
    """
    content = spec.read_text(encoding="utf-8")
    if "decision_consequence_map:" not in content:
        pytest.skip("CCT-DCM-01a fails — no DCM to check")

    blocks = _extract_dcm_blocks(content)
    violations: list[str] = []

    for block in blocks:
        for m in _DR_ENTRY_RE.finditer(block):
            decision_type = m.group(1).strip()
            entry_body = m.group(2)
            if "constitutional_basis" not in entry_body:
                violations.append(decision_type)

    assert not violations, (
        f"CCT-DCM-02b FAIL: {spec.name} — DETERMINISTIC_REQUIRED decisions missing "
        f"constitutional_basis:\n  {violations}\n"
        f"Add: constitutional_basis: C-XXX to each entry.\n"
        f"Constitutional basis: C-073 (annotation obligation), C-059 (traceability)."
    )

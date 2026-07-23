# Implements: tests/constitutional/README.md (CCT-PIPE-01)
# constitutional_basis: C-059 (Implementation Traceability), C-073 (Constitutional Annotations)
# ib_item: IB-009
# office: Platform IT Expert — Implementation hat
# produced_by: EA post-mortem 2026-07-23 (autonomous sprint pipeline review)
# QA sign-off: 2026-07-23

"""
CCT-PIPE-01 — Pipeline Script Syntax and C-073 Annotation Compliance

Runs on: every PR touching scripts/
Blocking: Yes — syntax errors or missing annotations block merge

Constitutional principle: Every pipeline script that enforces a constitutional
obligation must (a) compile without errors and (b) carry a C-073
# constitutional_basis: annotation. This CCT prevents the class of failures
seen in WC-011 runs #22–#27 where orphaned code caused SyntaxErrors in
production with no gate to catch them.
"""
import py_compile
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent

PIPELINE_SCRIPTS = [
    "scripts/autonomous_sprint_runner.py",
    "scripts/autonomous_sprint_reviewer.py",
    "scripts/build_sprint_index.py",
    "scripts/sprint_state.py",
    "scripts/sprint_status_reporter.py",
]


@pytest.mark.parametrize("script", PIPELINE_SCRIPTS)
def test_pipeline_script_compiles_without_syntax_error(script: str) -> None:
    """CCT-PIPE-01a: Every pipeline script must pass py_compile.

    A SyntaxError in a pipeline script causes the entire autonomous sprint
    to fail immediately with an unhelpful error. This test catches orphaned
    code, missing colons, bad indentation, and other syntax errors before
    they reach production.
    """
    script_path = str(REPO_ROOT / script)
    try:
        py_compile.compile(script_path, doraise=True)
    except py_compile.PyCompileError as e:
        pytest.fail(
            f"CCT-PIPE-01a FAIL: {script} has a syntax error.\n"
            f"Error: {e}\n"
            f"Constitutional basis: C-059 — every implementation must be traceable; "
            f"a script that doesn't compile is not an implementation."
        )


@pytest.mark.parametrize("script", PIPELINE_SCRIPTS)
def test_pipeline_script_carries_constitutional_annotation(script: str) -> None:
    """CCT-PIPE-01b: Every pipeline script must carry a constitutional_basis annotation (C-073).

    Pipeline scripts implement constitutional obligations (Evidence First C-023,
    SDLC Separation C-065, Authorization Tiers C-066). C-073 requires every
    implementation to carry a traceable annotation to the claims it implements.
    """
    content = (REPO_ROOT / script).read_text(encoding="utf-8")
    assert "constitutional_basis" in content, (
        f"CCT-PIPE-01b FAIL: {script} is missing a # constitutional_basis: annotation.\n"
        f"Add: # constitutional_basis: C-XXX, C-YYY (list claims this script enforces)\n"
        f"Constitutional basis: C-073 — every implementation must be annotated."
    )


@pytest.mark.parametrize("script", PIPELINE_SCRIPTS)
def test_pipeline_script_carries_ib_reference(script: str) -> None:
    """CCT-PIPE-01c: Every pipeline script must carry an ib_item reference (C-059).

    Every implementation must trace to an authorized backlog item.
    """
    content = (REPO_ROOT / script).read_text(encoding="utf-8")
    assert "ib_item" in content or "ib-" in content.lower(), (
        f"CCT-PIPE-01c FAIL: {script} is missing an ib_item reference.\n"
        f"Add: # ib_item: IB-009\n"
        f"Constitutional basis: C-059 — implementation traceability."
    )

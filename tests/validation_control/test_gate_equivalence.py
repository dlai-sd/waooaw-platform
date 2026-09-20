"""WC104-R015 authoritative gate-equivalence contracts."""

from copy import deepcopy
from pathlib import Path

import yaml

from validation_control.gate_equivalence import validate_gate_equivalence, workflow_catalog_gates


ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "validation/authoritative-gate-baseline.yaml"


def load_baseline() -> dict[str, object]:
    return yaml.safe_load(BASELINE_PATH.read_text(encoding="utf-8"))


def test_candidate_preserves_authoritative_gate_baseline() -> None:
    assert validate_gate_equivalence(ROOT, load_baseline()) == []


def test_missing_catalog_gate_fails_equivalence(tmp_path: Path) -> None:
    baseline = load_baseline()
    relative = ".github/workflows/integration-tests.yaml"
    workflow = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
    mutated = deepcopy(workflow)
    mutated["jobs"]["prompt-injection"]["steps"] = [
        step
        for step in mutated["jobs"]["prompt-injection"]["steps"]
        if step.get("uses") != "./.github/actions/run-validation-gate"
    ]
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    target.write_text(yaml.safe_dump(mutated), encoding="utf-8")
    for source in (
        "validation/engineering-validation.yaml",
        ".github/workflows/ci.yaml",
        ".github/workflows/code-quality.yaml",
        ".github/workflows/e2e-acceptance-tests.yaml",
    ):
        destination = tmp_path / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / source).read_bytes())
    for source in load_baseline()["thresholds"]:
        destination = tmp_path / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / source).read_bytes())

    violations = validate_gate_equivalence(tmp_path, baseline)

    assert "CATALOG_GATE_REMOVED:.github/workflows/integration-tests.yaml:security:prompt-injection" in violations


def test_matrix_and_literal_catalog_bindings_are_detected() -> None:
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    gates = workflow_catalog_gates(ci)

    assert "test-dotnet:constitutional-engine" in gates
    assert "test-python:ai-runtime" in gates
    assert "release-qualification" in gates

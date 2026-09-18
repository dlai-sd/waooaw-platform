import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "work-contracts/WC-100-baseline.json"
CANDIDATE = ROOT / "work-contracts/WC-100-candidate-measurement.json"
QUALIFICATION = ROOT / "scripts/run_wc100_qualification.sh"


def test_measurement_report_has_five_classes() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    expected = {"web-only", "business-platform", "python-service", "shared-contract", "pipeline-global"}

    assert {sample["change_class"] for sample in baseline["samples"]} == expected
    assert {sample["change_class"] for sample in candidate["samples"]} == expected
    assert baseline["summary"]["sample_size"] == candidate["summary"]["sample_size"] == 5
    assert candidate["summary"]["unsupported_savings_claims"] is False


def test_measurement_schema_separates_evidence_classes() -> None:
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))

    assert candidate["evidence_classes"] == {
        "baseline": "completed-github-ci",
        "candidate_hosted_wall_time": "untested-until-pr-ci",
        "candidate_selection": "local-deterministic-git-replay",
    }
    assert "percentage" not in json.dumps(candidate).lower()


def test_validation_lifecycle_trace_is_ordered() -> None:
    source = QUALIFICATION.read_text(encoding="utf-8")

    stages = [
        "validate_requirement_ledger.py",
        "pytest -q",
        "ruff check",
        "ruff format --check",
        "python scripts/validation_policy.py",
        "jq -n",
    ]
    positions = [source.index(stage) for stage in stages]
    assert positions == sorted(positions)


def test_qualification_container_fails_fast() -> None:
    source = QUALIFICATION.read_text(encoding="utf-8")
    container_commands = source.split("test-runner sh -lc '", maxsplit=1)[1]

    assert container_commands.lstrip().startswith("set -eu\n")


def test_changed_file_scope() -> None:
    allowed = (
        ".github/agent-context/office-platform-it-expert.md",
        ".github/workflows/ci.yaml",
        "architecture/reference/dockerfiles/Dockerfile.test-runner",
        "constitution/BOOTSTRAP.md",
        "constitution/PROJECT_STATE.md",
        "scripts/",
        "tests/pipeline/",
        "validation/",
        "work-contracts/",
    )
    scope = (ROOT / "validation/engineering-validation.yaml").read_text(encoding="utf-8")

    assert "mode: shadow" in scope
    assert all(
        path.startswith(allowed)
        for path in (
            ".github/agent-context/office-platform-it-expert.md",
            "architecture/reference/dockerfiles/Dockerfile.test-runner",
            "constitution/BOOTSTRAP.md",
            "constitution/PROJECT_STATE.md",
            "scripts/validation_policy.py",
            "tests/pipeline/test_validation_policy.py",
            "validation/engineering-validation.yaml",
            "work-contracts/WC-100-requirements.yaml",
        )
    )


def test_handoff_trace_is_complete() -> None:
    source = QUALIFICATION.read_text(encoding="utf-8")

    for field in ("commit_sha", "base_sha", "runner_image_id", "stages", "artifacts", "passed"):
        assert field in source

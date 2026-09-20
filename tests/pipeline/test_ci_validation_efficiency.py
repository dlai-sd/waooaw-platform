from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ROOT / ".github/workflows/ci.yaml"
RELEASE_QUALIFICATION_PATH = ROOT / "scripts/run_release_qualification.sh"
TEST_RUNNER_PATH = ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner"
CATALOG_PATH = ROOT / "validation/engineering-validation.yaml"
CATALOG_ACTION_PATH = ROOT / ".github/actions/run-validation-gate/action.yml"
RUNNER_ACTION_PATH = ROOT / ".github/actions/use-validation-runner/action.yml"
CATALOG_EXECUTION_PATH = ROOT / "scripts/validation_control/catalog_execution.py"
DOTNET_GATE_PATH = ROOT / "scripts/validation_control/run_dotnet_test_gate.sh"
PYTHON_GATE_PATH = ROOT / "scripts/validation_control/run_python_test_gate.sh"
DEPENDENCY_GATE_PATH = ROOT / "scripts/validation_control/run_dependency_scan_gate.sh"


def load_ci() -> dict[str, object]:
    return yaml.safe_load(CI_PATH.read_text(encoding="utf-8"))


def test_candidate_image_is_built_once_and_consumed_by_image_id() -> None:
    source = CI_PATH.read_text(encoding="utf-8")

    assert "id: candidate-build" in source
    assert "steps.candidate-build.outputs.imageid" in source
    assert "smoke_business_platform_image.sh '${{ steps.candidate-build.outputs.imageid }}'" in source
    assert "image-ref: ${{ steps.candidate-build.outputs.imageid }}" in source
    assert "scripts/record_build_evidence.sh" in source
    assert "actions/upload-artifact@v4" in source


def test_runner_images_are_verified_before_consumption() -> None:
    ci = CI_PATH.read_text(encoding="utf-8")
    catalog_action = CATALOG_ACTION_PATH.read_text(encoding="utf-8")
    runner_action = RUNNER_ACTION_PATH.read_text(encoding="utf-8")
    executor = CATALOG_EXECUTION_PATH.read_text(encoding="utf-8")

    assert ci.count("./.github/actions/run-validation-gate") >= 3
    assert "./.github/actions/use-validation-runner" in catalog_action
    assert 'gh attestation verify "oci://$image"' in runner_action
    assert 'docker pull "$image"' in runner_action
    assert "scripts/verify_runner_image.sh" in executor
    assert "WAOOAW_TEST_RUNNER_IMAGE_ID" in executor


def test_test_runner_contains_wc100_nested_docker_tools() -> None:
    source = TEST_RUNNER_PATH.read_text(encoding="utf-8")

    assert "    docker.io \\\n" in source
    assert "    docker-compose-v2 \\\n" in source
    assert "    jq \\\n" in source


def test_full_runner_avoids_post_copy_metadata_mutation() -> None:
    source = TEST_RUNNER_PATH.read_text(encoding="utf-8")

    assert "COPY --chown=waooaw:waooaw web/package.json web/pnpm-lock.yaml /opt/waooaw-web/" in source
    assert "COPY --chown=waooaw:waooaw . /workspace/" not in source
    assert "RUN chmod +x scripts/*.sh" not in source


def test_release_qualification_accepts_exact_runner_without_hidden_rebuild() -> None:
    source = RELEASE_QUALIFICATION_PATH.read_text(encoding="utf-8")

    assert 'if [ -z "${WAOOAW_TEST_RUNNER_IMAGE_ID:-}" ]; then' in source
    assert 'scripts/verify_runner_image.sh test test-runner "$WAOOAW_TEST_RUNNER_IMAGE_ID"' in source


def test_coverage_thresholds_are_unchanged() -> None:
    dotnet_gate = DOTNET_GATE_PATH.read_text(encoding="utf-8")
    python_gate = PYTHON_GATE_PATH.read_text(encoding="utf-8")
    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))

    assert "lines >= 0.90 && branches >= 0.80" in dotnet_gate
    assert "lines >= 90 and branches >= 80" in python_gate
    assert '"lines":90,"branches":80,"functions":90,"statements":90' in catalog["commands"]["test-web"]["shell"]


def test_required_gate_aggregation_is_preserved() -> None:
    ci = load_ci()
    needs = ci["jobs"]["qa-campaign"]["needs"]

    for gate in (
        "build",
        "secrets",
        "test-dotnet",
        "test-python",
        "test-web",
        "spec-lint",
        "sast",
        "dep-scan",
        "constitutional-commit-gate",
        "author-review-gate",
    ):
        assert gate in needs


def test_shadow_mode_keeps_full_ci_authoritative() -> None:
    source = CI_PATH.read_text(encoding="utf-8")
    ci = load_ci()
    plan_workflow = (CI_PATH.parent / "validation-plan.yaml").read_text(encoding="utf-8")

    assert "validation/engineering-validation.yaml" in plan_workflow
    assert "WC-102 validation plan (Shadow)" in plan_workflow
    assert "chmod 0777 test-results/wc102" in plan_workflow
    assert ci["jobs"]["validation-plan"]["uses"] == "./.github/workflows/validation-plan.yaml"
    assert ci["jobs"]["build"]["if"] == "github.event_name == 'pull_request'"
    assert "validation-plan" in ci["jobs"]["qa-campaign"]["needs"]
    assert "build" in ci["jobs"]["qa-campaign"]["needs"]


def test_language_tests_use_docker_runners() -> None:
    catalog = CATALOG_PATH.read_text(encoding="utf-8")
    executor = CATALOG_EXECUTION_PATH.read_text(encoding="utf-8")
    python_gate = PYTHON_GATE_PATH.read_text(encoding="utf-8")
    dependency_gate = DEPENDENCY_GATE_PATH.read_text(encoding="utf-8")

    assert "profile: test-python" in catalog
    assert "profile: test-dotnet" in catalog
    assert "profile: test-ts" in catalog
    assert '"compose"' in executor
    assert '"--pull"' in executor and '"never"' in executor
    assert "export COVERAGE_FILE=/tmp/.coverage" in python_gate
    assert 'export BaseIntermediateOutputPath="/tmp/dependency-audit/$project_name/obj/"' in dependency_gate

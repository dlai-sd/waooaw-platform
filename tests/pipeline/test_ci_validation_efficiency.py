from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CI_PATH = ROOT / ".github/workflows/ci.yaml"
RELEASE_QUALIFICATION_PATH = ROOT / "scripts/run_release_qualification.sh"


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
    source = CI_PATH.read_text(encoding="utf-8")

    assert source.count("id: runner-build") >= 3
    assert source.count("scripts/verify_runner_image.sh") >= 3
    assert "WAOOAW_TEST_RUNNER_IMAGE_ID" in source


def test_release_qualification_accepts_exact_runner_without_hidden_rebuild() -> None:
    source = RELEASE_QUALIFICATION_PATH.read_text(encoding="utf-8")

    assert 'if [ -z "${WAOOAW_TEST_RUNNER_IMAGE_ID:-}" ]; then' in source
    assert 'scripts/verify_runner_image.sh test test-runner "$WAOOAW_TEST_RUNNER_IMAGE_ID"' in source


def test_coverage_thresholds_are_unchanged() -> None:
    source = CI_PATH.read_text(encoding="utf-8")

    assert "lines >= 0.90 && branches >= 0.80" in source
    assert '"lines":90,"branches":80,"functions":90,"statements":90' in source


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


def test_language_tests_use_docker_runners() -> None:
    source = CI_PATH.read_text(encoding="utf-8")

    assert "docker compose --profile test-python run" in source
    assert "docker compose --profile test-dotnet run" in source
    assert "docker compose --profile test-ts run" in source

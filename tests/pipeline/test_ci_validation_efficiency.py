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
DOTNET_QUALITY_GATE_PATH = ROOT / "scripts/validation_control/run_dotnet_quality_gate.sh"
PYTHON_GATE_PATH = ROOT / "scripts/validation_control/run_python_test_gate.sh"
DEPENDENCY_GATE_PATH = ROOT / "scripts/validation_control/run_dependency_scan_gate.sh"
DOTNET_RUNNER_PATH = ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet"
STATIC_PREFLIGHT_PATH = ROOT / "scripts/run_static_validation_preflight.sh"
IDENTITY_TEST_PATH = ROOT / "tests/business-platform.Tests/Identity"


def load_ci() -> dict[str, object]:
    return yaml.safe_load(CI_PATH.read_text(encoding="utf-8"))


def test_high_volume_identity_postgres_tests_reuse_servers_with_isolated_databases() -> None:
    fixture = (IDENTITY_TEST_PATH / "IdentityPostgresServerFixture.cs").read_text(encoding="utf-8")
    test_files = [
        IDENTITY_TEST_PATH / "CustomerWorkspaceProvisioningPostgresTests.cs",
        IDENTITY_TEST_PATH / "CustomerIdentityJourneyHttpPostgresTests.cs",
    ]

    assert "CREATE DATABASE" in fixture
    assert "DROP DATABASE" in fixture and "WITH (FORCE)" in fixture
    for path in test_files:
        source = path.read_text(encoding="utf-8")
        assert "IClassFixture<IdentityPostgresServerFixture>" in source
        assert "new PostgreSqlBuilder" not in source


def test_dotnet_vulnerability_audit_has_one_owning_gate() -> None:
    quality_gate = DOTNET_QUALITY_GATE_PATH.read_text(encoding="utf-8")
    dependency_gate = DEPENDENCY_GATE_PATH.read_text(encoding="utf-8")

    assert "package --vulnerable --include-transitive" not in quality_gate
    assert 'dotnet list "$1" package --vulnerable --include-transitive' in dependency_gate


def test_dotnet_runner_installs_only_required_python_bootstrap_dependencies() -> None:
    dockerfile = DOTNET_RUNNER_PATH.read_text(encoding="utf-8")

    assert "python3" in dockerfile
    for dependency in (
        "aiosqlite>=0.20",
        "asyncpg==0.30.0",
        "cryptography==50.0.0",
        "fastapi==0.135.1",
        "httpx==0.27.2",
        "pyyaml>=6.0",
        "redis==5.2.0",
        "sqlalchemy[asyncio]==2.0.36",
        "uvicorn==0.30.6",
    ):
        assert dependency in dockerfile
    assert "requirements-test.txt" not in dockerfile


def test_release_qualification_reports_each_parallel_lane_duration() -> None:
    release_runner = RELEASE_QUALIFICATION_PATH.read_text(encoding="utf-8")

    assert "run_release_lane()" in release_runner
    for lane in ("tests", "postgres", "demo-data", "simulator", "azure"):
        assert f"run_release_lane {lane}" in release_runner
    assert "event=STARTED" in release_runner
    assert "event=COMPLETED" in release_runner
    assert "duration_seconds=" in release_runner


def test_static_preflight_blocks_runner_supply_and_compiles_docker_graphs() -> None:
    ci = load_ci()
    source = STATIC_PREFLIGHT_PATH.read_text(encoding="utf-8")

    assert ci["jobs"]["runner-supply"]["needs"] == "static-preflight"
    assert "static-preflight" in ci["jobs"]["qa-campaign"]["needs"]
    checkout = ci["jobs"]["static-preflight"]["steps"][0]
    assert checkout["with"]["fetch-depth"] == 0
    preflight = ci["jobs"]["static-preflight"]["steps"][-1]
    assert "github.event.pull_request.base.sha" in preflight["env"]["BASE_SHA"]
    assert "github.event.pull_request.head.sha" in preflight["env"]["HEAD_SHA"]
    assert "rhysd/actionlint:1.7.7" in source
    assert "git diff --name-only --diff-filter=ACMR" in source
    assert "git diff --cached --name-only" in source
    assert "docker compose config --quiet" in source
    assert source.count("docker buildx build --check") == 1
    assert "src/constitutional-engine/Dockerfile" in source
    assert "src/agent-adapters/digital_marketing/Dockerfile" in source
    assert "--push" not in source


def test_candidate_image_is_built_once_and_consumed_by_image_id() -> None:
    source = CI_PATH.read_text(encoding="utf-8")
    ci = load_ci()

    assert "id: candidate-build" in source
    assert "steps.candidate-build.outputs.imageid" in source
    assert "smoke_business_platform_image.sh '${{ steps.candidate-build.outputs.imageid }}'" in source
    assert "image-ref: ${{ steps.candidate-build.outputs.imageid }}" in source
    assert "scripts/record_build_evidence.sh" in source
    assert "actions/upload-artifact@v4" in source
    assert ci["jobs"]["build"]["needs"] == "validation-plan"
    assert ci["jobs"]["build"]["strategy"]["matrix"]["service"] == (
        "${{ fromJSON(needs.validation-plan.outputs.service_build_matrix) }}"
    )
    assert "has_service_builds == 'true'" in ci["jobs"]["build"]["if"]


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


def test_release_qualification_scopes_and_parallelizes_independent_lanes() -> None:
    source = RELEASE_QUALIFICATION_PATH.read_text(encoding="utf-8")

    assert "qualification_change_scope.py" in source
    assert "WAOOAW_HOST_CHANGED_FILES_FILE" in source
    assert source.index("qualification_change_scope.py") < source.index("run_docker_build.sh")
    assert 'RELEASE_RUN_TESTS" = true || test "$RELEASE_RUN_POSTGRES" = true || test "$RELEASE_RUN_SIMULATOR" = true' in source
    for lane in ("TESTS", "POSTGRES", "DEMO_DATA", "SIMULATOR", "AZURE"):
        assert f'RELEASE_RUN_{lane}" = true' in source
    assert source.count("_pid=$!") == 5
    assert source.index("azure_pid=$!") < source.index('for lane_pid in "$tests_pid"')


def test_coverage_thresholds_are_unchanged() -> None:
    dotnet_gate = DOTNET_GATE_PATH.read_text(encoding="utf-8")
    python_gate = PYTHON_GATE_PATH.read_text(encoding="utf-8")
    web_gate = (ROOT / "scripts/validation_control/run_web_test_gate.sh").read_text(encoding="utf-8")

    assert "lines >= 0.90 && branches >= 0.80" in dotnet_gate
    assert "lines >= 90 and branches >= 80" in python_gate
    assert '"lines":90,"branches":80,"functions":90,"statements":90' in web_gate


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


def test_costly_ci_jobs_are_guarded_by_the_validation_plan() -> None:
    ci = load_ci()

    assert ci["jobs"]["test-dotnet"]["if"] == "needs.validation-plan.outputs.dotnet_test_matrix != '[]'"
    assert ci["jobs"]["test-python"]["if"] == "needs.validation-plan.outputs.python_test_matrix != '[]'"
    for job_id in ("test-web", "spec-lint", "sast", "dep-scan", "license-check"):
        condition = ci["jobs"][job_id].get("if", "")
        assert "needs.validation-plan.outputs.execution_gates" in condition, job_id
        assert "validation-plan" in (
            [ci["jobs"][job_id]["needs"]] if isinstance(ci["jobs"][job_id]["needs"], str) else ci["jobs"][job_id]["needs"]
        ), job_id
    assert "needs.validation-plan.outputs.release_required == 'true'" in ci["jobs"]["release-qualification"]["if"]
    assert "needs.qualification-control.outputs.enabled == 'true'" in ci["jobs"]["release-qualification"]["if"]
    assert set(ci["jobs"]["release-qualification"]["needs"]) == {
        "runner-supply",
        "validation-plan",
        "qualification-control",
    }


def test_release_qualification_control_is_founder_bound_and_push_fail_closed() -> None:
    control = load_ci()["jobs"]["qualification-control"]
    source = control["steps"][0]["run"]

    assert control["outputs"]["enabled"] == "${{ steps.control.outputs.enabled }}"
    assert 'authority="push-to-main"' in source
    assert 'if [[ "$EVENT_NAME" == "pull_request" ]]' in source
    assert "Release Qualification:" in source
    assert "(ON|OFF)" in source
    assert "OFF requires one non-placeholder Founder authority record" in source


def test_main_release_manifest_fails_when_a_prerequisite_is_not_successful() -> None:
    release_manifest = load_ci()["jobs"]["release-manifest"]

    assert release_manifest["if"] == ("always() && github.event_name == 'push' && github.ref == 'refs/heads/main'")
    prerequisite = release_manifest["steps"][0]
    assert prerequisite["name"] == "Require successful exact-seven validation prerequisites"
    assert set(prerequisite["env"]) == {
        "PUBLISH_RESULT",
        "SECRETS_RESULT",
        "DOTNET_RESULT",
        "PYTHON_RESULT",
        "WEB_RESULT",
        "SPEC_LINT_RESULT",
        "SAST_RESULT",
        "TRIVY_RESULT",
        "DEPENDENCY_SCAN_RESULT",
        "LICENSE_RESULT",
    }
    assert 'test "$result" = success' in prerequisite["run"]


def test_shadow_mode_keeps_full_main_publication_authoritative() -> None:
    ci = load_ci()
    plan_workflow = (CI_PATH.parent / "validation-plan.yaml").read_text(encoding="utf-8")

    assert "validation/engineering-validation.yaml" in plan_workflow
    assert "WC-102 validation plan (Shadow)" in plan_workflow
    assert "chmod 0777 test-results/wc102" in plan_workflow
    assert ci["jobs"]["validation-plan"]["uses"] == "./.github/workflows/validation-plan.yaml"
    assert "needs.validation-plan.outputs.has_service_builds == 'true'" in ci["jobs"]["build"]["if"]
    assert ci["jobs"]["publish"]["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    assert len(ci["jobs"]["publish"]["strategy"]["matrix"]["service"]) == 7
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

"""WC102-01/02 runner boundary tests."""

# Implements: work-contracts/WC-102-docker-only-validation-control-plane.md §4.3-4.12
# Constitutional basis: C-059, C-071, C-080

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
RUNNERS = ("test-runner-python", "test-runner-dotnet", "test-runner-ts")


def test_default_network_is_project_scoped() -> None:
    assert "name" not in COMPOSE
    assert "default" not in COMPOSE["networks"]


def test_stack_runners_are_non_root_bounded_and_source_mounted() -> None:
    for runner_name in RUNNERS:
        runner = COMPOSE["services"][runner_name]
        assert runner["read_only"] is True
        assert runner["cap_drop"] == ["ALL"]
        assert runner["security_opt"] == ["no-new-privileges:true"]
        assert runner["cpus"] == 2.0
        assert runner["mem_limit"] == "4g"
        assert runner["pids_limit"] == 512

    assert ".:/workspace:ro" in COMPOSE["services"]["test-runner-python"]["volumes"]
    assert ".:/workspace:ro" in COMPOSE["services"]["test-runner-dotnet"]["volumes"]
    typescript_volumes = COMPOSE["services"]["test-runner-ts"]["volumes"]
    assert ".:/workspace:ro" in typescript_volumes
    assert "./test-results:/workspace/test-results" in typescript_volumes
    assert all(":/workspace/web/" not in volume for volume in typescript_volumes)
    assert all(":/workspace/web/" not in volume for volume in COMPOSE["services"]["test-runner"]["volumes"])


def test_socket_is_absent_from_every_runner_by_default() -> None:
    for runner_name in (*RUNNERS, "test-runner"):
        runner = COMPOSE["services"][runner_name]
        assert all("docker.sock" not in volume for volume in runner["volumes"])


def test_stack_runners_declare_non_root_uid_and_gid() -> None:
    for runner_name in (*RUNNERS, "test-runner"):
        assert COMPOSE["services"][runner_name]["user"] == "1000:1000"


def test_runner_images_exclude_application_source() -> None:
    dockerfiles = [
        ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-python",
        ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet",
        ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-ts",
        ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner",
    ]

    for dockerfile in dockerfiles:
        source = dockerfile.read_text(encoding="utf-8")
        assert "COPY . /workspace" not in source
        assert "COPY --chown=waooaw:waooaw . /workspace" not in source
        assert "USER root" not in source


def test_primary_service_build_contexts_match_root_relative_dockerfiles() -> None:
    for service in (
        "constitutional-engine",
        "business-platform",
        "professional-runtime",
        "ai-runtime",
        "billing-engine",
        "web",
    ):
        build = COMPOSE["services"][service]["build"]
        assert build["context"] == "."
        assert build["dockerfile"] in {f"src/{service}/Dockerfile", "web/Dockerfile"}


def test_compose_accepts_only_explicit_supplied_runner_images() -> None:
    expected = {
        "test-runner-python": "${WAOOAW_RUNNER_PYTHON_IMAGE:-waooaw-platform-test-runner-python:local}",
        "test-runner-dotnet": "${WAOOAW_RUNNER_DOTNET_IMAGE:-waooaw-platform-test-runner-dotnet:local}",
        "test-runner-ts": "${WAOOAW_RUNNER_TYPESCRIPT_IMAGE:-waooaw-platform-test-runner-typescript:local}",
        "test-runner": "${WAOOAW_RUNNER_FULL_IMAGE:-waooaw-platform-test-runner-full:local}",
    }

    for service, image in expected.items():
        assert COMPOSE["services"][service]["image"] == image


def test_dotnet_immutable_dependencies_are_not_masked_by_a_mutable_volume() -> None:
    dockerfile = (ROOT / "architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet").read_text(encoding="utf-8")
    volumes = COMPOSE["services"]["test-runner-dotnet"]["volumes"]

    assert "NUGET_PACKAGES=/opt/nuget/packages" in dockerfile
    assert all(":/opt/nuget/packages" not in volume for volume in volumes)
    assert "/tmp/nuget" not in str(COMPOSE["services"]["test-runner-dotnet"])


def test_dotnet_native_and_process_fixtures_use_bounded_executable_tmpfs() -> None:
    runner = COMPOSE["services"]["test-runner-dotnet"]

    assert runner["tmpfs"] == ["/tmp:size=2g,mode=1777,exec"]


def test_python_audit_builds_use_bounded_executable_tmpfs() -> None:
    runner = COMPOSE["services"]["test-runner-python"]

    assert runner["tmpfs"] == ["/tmp:size=1g,mode=1777,exec"]


def test_full_runner_fixtures_use_bounded_executable_tmpfs() -> None:
    runner = COMPOSE["services"]["test-runner"]

    assert (ROOT / ".deepeval").is_dir()
    assert runner["tmpfs"] == [
        "/tmp:size=2g,mode=1777,exec",
        "/workspace/.deepeval:size=16m,mode=1770",
    ]


def test_contract_workflow_starts_services_and_blocks_on_failure() -> None:
    workflow = (ROOT / ".github/workflows/integration-tests.yaml").read_text(encoding="utf-8")
    contract_job = workflow.split("  contract-rest:", maxsplit=1)[1].split("\n  seed-prompts-contract:", maxsplit=1)[0]
    contract_gate = (ROOT / "scripts/validation_control/run_rest_contract_gate.sh").read_text(encoding="utf-8")

    assert "docker compose up --detach --wait" in contract_gate
    assert "business-platform professional-runtime" in contract_gate
    assert "COMPOSE_PROJECT_NAME" not in contract_gate
    assert contract_gate.count("cd /tmp && schemathesis run /workspace/") == 2
    assert "--report-junit-path /workspace/test-results/schemathesis-bp.xml" in contract_gate
    assert "--report-junit-path /workspace/test-results/schemathesis-pr.xml" in contract_gate
    assert "gate-id: contract:rest" in contract_job
    assert "continue-on-error: true" not in contract_job
    assert COMPOSE["services"]["keycloak"]["environment"]["DEV_TEST_PASSWORD"] == (
        "${DEV_TEST_PASSWORD:-Waooaw-local-dev-only-1!}"
    )
    assert COMPOSE["services"]["keycloak"]["environment"]["KC_HEALTH_ENABLED"] == "true"
    assert COMPOSE["services"]["keycloak"]["healthcheck"]["test"][:3] == ["CMD", "/bin/bash", "-c"]
    assert "127.0.0.1/9000" in COMPOSE["services"]["keycloak"]["healthcheck"]["test"][3]
    assert COMPOSE["services"]["constitutional-engine"]["healthcheck"]["test"] == [
        "CMD",
        "grpc_health_probe",
        "-addr=localhost:5002",
    ]
    assert (
        COMPOSE["services"]["business-platform"]["environment"]["Conversation__CursorHmacKey"]
        == "${CONVERSATION_CURSOR_HMAC_KEY:-waooaw-conversation-cursor-local-dev-only}"
    )
    assert COMPOSE["services"]["professional-runtime"]["healthcheck"]["test"] == [
        "CMD",
        "python",
        "-c",
        "import urllib.request; urllib.request.urlopen('http://localhost:5003/health', timeout=3)",
    ]


def test_accessibility_gate_runs_required_product_states_and_emits_native_evidence() -> None:
    gate = (ROOT / "scripts/validation_control/run_accessibility_gate.sh").read_text(encoding="utf-8")

    assert "tests/e2e/f1-acceptance.spec.ts" in gate
    assert 'UX-RESP-01|CCT-UX-A11Y-01|active relationship Stop' in gate
    assert "--project chromium-expanded" in gate
    assert "--project chromium-compact-360" in gate
    assert 'PLAYWRIGHT_JUNIT_OUTPUT_FILE="$workspace/test-results/accessibility.xml"' in gate
    assert 'PLAYWRIGHT_HTML_OUTPUT_DIR="$report_directory"' in gate

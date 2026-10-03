"""WC102-01/02 runner boundary tests."""

# Implements: work-contracts/WC-102-docker-only-validation-control-plane.md §4.3-4.12
# Constitutional basis: C-059, C-071, C-080

from pathlib import Path
import tomllib

import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
DYNAMIC_CONFIG = yaml.safe_load((ROOT / "infrastructure/temporal/dynamicconfig.yaml").read_text(encoding="utf-8"))
VALIDATION_CATALOG = yaml.safe_load((ROOT / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
SCHEMATHESIS = tomllib.loads((ROOT / "validation/schemathesis.toml").read_text(encoding="utf-8"))
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


def test_business_platform_test_gate_requests_testcontainers_socket() -> None:
    resources = VALIDATION_CATALOG["gates"]["test-dotnet:business-platform"]["resources"]

    assert resources["docker_socket"] is True
    assert resources["socket_classification"] == "testcontainers"
    assert VALIDATION_CATALOG["gates"]["test-dotnet:business-platform"]["environment"] == ["TESTCONTAINERS_HOST_OVERRIDE"]


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


def test_web_dependency_patches_are_bound_to_every_installing_runner() -> None:
    for dockerfile_name in ("Dockerfile.test-runner-ts", "Dockerfile.test-runner"):
        source = (ROOT / "architecture/reference/dockerfiles" / dockerfile_name).read_text(encoding="utf-8")
        assert "web/patches/" in source

    runners = VALIDATION_CATALOG["prechecks"]["typescript_dependency_scan"]["inputs"]
    assert "web/patches/**" in runners
    gate = (ROOT / "scripts/validation_control/run_dependency_scan_gate.sh").read_text(encoding="utf-8")
    assert gate.index("verify-security-patches.js") < gate.index("pnpm audit --audit-level high")


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


def test_typescript_native_dependencies_use_bounded_executable_tmpfs() -> None:
    runner = COMPOSE["services"]["test-runner-ts"]

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

    assert "docker compose up --detach --no-build --wait" in contract_gate
    assert "business-platform professional-runtime" in contract_gate
    assert "COMPOSE_PROJECT_NAME" not in contract_gate
    assert (
        contract_gate.count("cd /tmp && schemathesis --config-file /workspace/validation/schemathesis.toml run /workspace/") == 5
    )
    assert '--include-path-regex "$customer_product_path_regex"' in contract_gate
    assert '--include-path-regex "$customer_identity_path_regex"' in contract_gate
    assert "--identity-token-file /tmp/business-platform-identity-token" in contract_gate
    assert contract_gate.count('-H "Authorization:Bearer $identity_token"') == 2
    assert '--exclude-path-regex "$customer_path_regex"' in contract_gate
    assert contract_gate.count("--suppress-health-check=filter_too_much") == 5
    assert "WAOOAW_VALIDATION_OUTPUT_DIRECTORY" in contract_gate
    assert contract_gate.count('--volume "$validation_output_directory:/workspace/test-results"') == 2
    assert SCHEMATHESIS["checks"]["positive_data_acceptance"]["expected-statuses"] == [
        "2xx",
        "401",
        "403",
        "404",
        "409",
        "410",
        "429",
        "5xx",
    ]
    assert contract_gate.index('test "$customer_product_status" -eq 0') < contract_gate.index("merge_junit_reports.py")
    assert "rm -f /workspace/test-results/schemathesis-bp.xml" in contract_gate
    assert "merge_junit_reports.py" in contract_gate
    assert "--output /workspace/test-results/schemathesis-bp.xml" in contract_gate
    assert '--exclude-path-regex "^/health$"' in contract_gate
    assert '--include-path-regex "^/health$"' in contract_gate
    assert contract_gate.count("--exclude-checks not_a_server_error") == 1
    assert "--output /workspace/test-results/schemathesis-pr.xml" in contract_gate
    assert "schemathesis-pr-service.xml" in contract_gate
    assert "schemathesis-pr-health.xml" in contract_gate
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
    assert COMPOSE["services"]["business-platform"]["environment"]["Temporal__Host"] == "temporal:7233"
    assert COMPOSE["services"]["business-platform"]["depends_on"]["temporal"]["condition"] == "service_healthy"
    assert "tctl --address" in COMPOSE["services"]["temporal"]["healthcheck"]["test"][-1]
    assert (
        COMPOSE["services"]["business-platform"]["environment"]["ChannelContinuity__EnvelopeHmacKey"]
        == "${CHANNEL_CONTINUITY_HMAC_KEY:-d2Fvb2F3LWNvbnRpbnVpdHktbG9jYWwtZGV2LWtleSE=}"
    )
    assert (
        COMPOSE["services"]["business-platform"]["environment"]["Voice__ContentEncryptionKey"]
        == "${VOICE_CONTENT_ENCRYPTION_KEY:-d2Fvb2F3LXZvaWNlLWNvbnRlbnQtbG9jYWwta2V5ISE=}"
    )
    assert COMPOSE["services"]["professional-runtime"]["healthcheck"]["test"] == [
        "CMD",
        "python",
        "-c",
        "import urllib.request; urllib.request.urlopen('http://localhost:5003/health', timeout=3)",
    ]


def test_customer_contract_rejects_unpersistable_fuzz_inputs_and_documents_step_up() -> None:
    specification = yaml.safe_load(
        (ROOT / "architecture/reference/api-specs/business-platform.openapi.yaml").read_text(encoding="utf-8")
    )
    paths = specification["paths"]
    schemas = specification["components"]["schemas"]

    for path in (
        "/api/v1/identity/registrations",
        "/api/v1/identity/registrations/{registrationId}/complete",
    ):
        assert paths[path]["post"]["responses"]["403"] == {"$ref": "#/components/responses/IdentityStepUpRequired"}
    assert schemas["ConversationLanguageTag"]["pattern"] == "^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"
    assert schemas["ConversationTextBlockV1"]["properties"]["text"]["pattern"] == r"^(?=.*\S)[^\u0000]+$"
    for request_schema in ("SendPortalInteractionMessageRequestV1", "SendConversationMessageRequestV1"):
        assert schemas[request_schema]["properties"]["locale"] == {"$ref": "#/components/schemas/ConversationLanguageTag"}


def test_temporal_dynamic_config_uses_native_scalar_types() -> None:
    assert DYNAMIC_CONFIG["system.forceSearchAttributesCacheRefreshOnRead"][0]["value"] is True
    for key in (
        "limit.maxIDLength",
        "frontend.namespaceRPS",
        "frontend.globalNamespaceRPS",
        "matching.numTaskqueueReadPartitions",
        "matching.numTaskqueueWritePartitions",
    ):
        value = DYNAMIC_CONFIG[key][0]["value"]
        assert isinstance(value, int) and not isinstance(value, bool)


def test_accessibility_gate_runs_required_product_states_and_emits_native_evidence() -> None:
    gate = (ROOT / "scripts/validation_control/run_accessibility_gate.sh").read_text(encoding="utf-8")

    assert "tests/e2e/f1-acceptance.spec.ts" in gate
    assert "UX-RESP-01|CCT-UX-A11Y-01|active relationship Stop" in gate
    assert "--project chromium-expanded" in gate
    assert "--project chromium-compact-360" in gate
    assert 'PLAYWRIGHT_JUNIT_OUTPUT_FILE="$workspace/test-results/accessibility.xml"' in gate
    assert 'PLAYWRIGHT_HTML_OUTPUT_DIR="$report_directory"' in gate

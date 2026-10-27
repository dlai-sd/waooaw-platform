"""P2-WC02 seven-member packaging and baseline Compose contracts."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).parents[2]
COMPOSE_FILE = REPO_ROOT / "docker-compose.release.yml"
RELEASE_MEMBERS = {
    "constitutional-engine": ("5002", ".", "src/constitutional-engine/Dockerfile"),
    "business-platform": ("5001", ".", "src/business-platform/Dockerfile"),
    "professional-runtime": ("5003", ".", "src/professional-runtime/Dockerfile"),
    "ai-runtime": ("5004", ".", "src/ai-runtime/Dockerfile"),
    "web": ("3000", ".", "web/Dockerfile"),
    "billing-engine": ("8140", ".", "src/billing-engine/Dockerfile"),
    "agent-runtime-adapter-digital-marketing": (
        "8443",
        "src",
        "digital-marketing-agent/Dockerfile",
    ),
}
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yaml"
DEBIAN_RUNTIME_DOCKERFILES = (
    "src/constitutional-engine/Dockerfile",
    "src/business-platform/Dockerfile",
    "src/professional-runtime/Dockerfile",
    "src/ai-runtime/Dockerfile",
    "src/billing-engine/Dockerfile",
)
PYTHON_DEPENDENCY_DOCKERFILES = (
    "src/professional-runtime/Dockerfile",
    "src/ai-runtime/Dockerfile",
    "src/billing-engine/Dockerfile",
)


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))


def test_exactly_seven_release_members_have_explicit_builds() -> None:
    services = _compose()["services"]
    for member, (_, context, dockerfile) in RELEASE_MEMBERS.items():
        assert member in services
        assert (REPO_ROOT / context / dockerfile).is_file()
        build = services[member]["build"]
        assert build["context"] == context
        assert build["dockerfile"] == dockerfile


def test_ci_publishes_only_main_with_attestations_and_digest_artifacts() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    jobs = yaml.safe_load(workflow)["jobs"]
    build = jobs["build"]
    publish = jobs["publish"]
    policy = yaml.safe_load((REPO_ROOT / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    pull_request_services = [
        {
            "name": component["service_image"],
            "context": component["service_context"],
            "dockerfile": component["service_dockerfile"],
        }
        for component in policy["components"].values()
    ]
    for services in (pull_request_services, publish["strategy"]["matrix"]["service"]):
        assert all((REPO_ROOT / service["dockerfile"]).is_file() for service in services)
        dma = next(
            service
            for service in services
            if service["name"] == "agent-runtime-adapter-digital-marketing"
        )
        assert dma["context"] == "src"
        assert dma["dockerfile"] == "src/digital-marketing-agent/Dockerfile"
    assert "needs.validation-plan.outputs.has_service_builds == 'true'" in build["if"]
    assert build["permissions"] == {"contents": "read", "security-events": "write"}
    assert publish["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    assert publish["permissions"] == {
        "contents": "read",
        "packages": "write",
        "id-token": "write",
        "attestations": "write",
    }
    assert "push: false" in workflow
    assert "load: true" in workflow
    assert "sbom: false" in workflow
    assert "provenance: false" in workflow
    # Exactly two publication points, both main-only: the exact-seven release and the runner images.
    assert workflow.count("push: true") == 2
    assert "publish-runner-images:" in workflow
    assert workflow.count("if: github.event_name == 'push' && github.ref == 'refs/heads/main'") >= 2
    assert "sbom: true" in workflow
    assert "provenance: mode=max" in workflow
    assert "steps.image.outputs.digest" in workflow
    assert "goal006-digest-${{ matrix.service.name }}" in workflow
    assert "goal006-attestation-${{ matrix.service.name }}" in workflow
    assert "docker buildx imagetools inspect" in workflow
    assert "subject-digest: ${{ steps.image.outputs.digest }}" in workflow
    assert "push-to-registry: true" in workflow
    assert "Scan pull-request image" in workflow
    assert "release-manifest:" in workflow
    assert "python scripts/goal006_registry_manifest.py" in workflow
    assert "actions/attest-build-provenance@v2" in workflow
    assert "attestations: write" in workflow
    assert "goal006-exact-seven-release-${{ github.sha }}" in workflow


def test_ci_has_deterministic_spec_and_fixable_vulnerability_gates() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    spectral = (REPO_ROOT / ".spectral.yaml").read_text(encoding="utf-8")
    spec_gate = (REPO_ROOT / "scripts/validation_control/run_spec_lint_gate.sh").read_text(encoding="utf-8")
    assert "spectral:oas" in spectral
    assert "stoplight/spectral:6.15.0" in spec_gate
    assert "openapitools/openapi-generator-cli:v7.17.0" in spec_gate
    assert "spec_lint_scope.py" in spec_gate
    assert "bufbuild/buf:1.72.0" in spec_gate
    assert "Detect affected image" not in workflow
    assert "steps.affected.outputs.build" not in workflow
    assert workflow.count("Build pull-request image") == 1
    assert workflow.count("Scan pull-request image") == 1
    assert workflow.count("scanners: vuln") == 2
    assert workflow.count("ignore-unfixed: true") == 2
    assert workflow.count("severity: CRITICAL,HIGH") == 2
    assert workflow.count("exit-code: 1") >= 2


def test_hosted_builds_refresh_debian_runtime_security_layers() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("SECURITY_REFRESH=${{ github.run_id }}") == 2

    for dockerfile in DEBIAN_RUNTIME_DOCKERFILES:
        content = (REPO_ROOT / dockerfile).read_text(encoding="utf-8")
        assert "ARG SECURITY_REFRESH=local" in content
        assert 'RUN test -n "$SECURITY_REFRESH"' in content
        assert content.index('RUN test -n "$SECURITY_REFRESH"') < content.index(
            "apt-get update"
        )

    for dockerfile in PYTHON_DEPENDENCY_DOCKERFILES:
        content = (REPO_ROOT / dockerfile).read_text(encoding="utf-8")
        first_stage = content.index("FROM ")
        second_stage = content.index("\nFROM ", first_stage) + 1
        dependency_stage = content[first_stage:second_stage]
        assert "ARG SECURITY_REFRESH=local" in dependency_stage
        assert dependency_stage.index('RUN test -n "$SECURITY_REFRESH"') < (
            dependency_stage.index("pip install")
        )


def test_release_images_are_non_root_and_expose_accepted_ports() -> None:
    for _, (port, context, dockerfile) in RELEASE_MEMBERS.items():
        content = (REPO_ROOT / context / dockerfile).read_text(encoding="utf-8")
        assert "USER " in content
        assert "USER root" not in content
        assert f"EXPOSE {port}" in content


def test_release_images_pin_fixed_security_dependencies() -> None:
    constitutional_engine = (
        REPO_ROOT / "src/constitutional-engine/Dockerfile"
    ).read_text(encoding="utf-8")
    business_platform = (REPO_ROOT / "src/business-platform/Dockerfile").read_text(
        encoding="utf-8"
    )
    ai_requirements = (REPO_ROOT / "src/ai-runtime/requirements.txt").read_text(
        encoding="utf-8"
    )
    professional_requirements = (
        REPO_ROOT / "src/professional-runtime/requirements.txt"
    ).read_text(encoding="utf-8")
    billing_requirements = (
        REPO_ROOT / "src/billing-engine/requirements.txt"
    ).read_text(encoding="utf-8")
    web_package = (REPO_ROOT / "web/package.json").read_text(encoding="utf-8")

    assert (
        "golang:1.26.10-alpine@sha256:9ce231b28998b32e116927c61aa5c406183061d4f3f2d61b292c88e7f6bdf7ca"
        in constitutional_engine
    )
    assert "GRPC_GO_VERSION=v1.83.2" in constitutional_engine
    fixed_aspnet_runtime = (
        "mcr.microsoft.com/dotnet/aspnet:9.0.21"
        "@sha256:4d94cf3204df98d321e8dbf8d6d06e0b34fd136aa75c945abf4390ee07eb30dd"
    )
    assert fixed_aspnet_runtime in constitutional_engine
    assert fixed_aspnet_runtime in business_platform
    assert "transformers==5.10.0" in ai_requirements
    for requirements in (professional_requirements, ai_requirements):
        assert "opentelemetry-api==1.45.1" in requirements
        assert "opentelemetry-sdk==1.45.1" in requirements
        assert "opentelemetry-exporter-otlp==1.45.1" in requirements
        assert "opentelemetry-instrumentation-fastapi==0.66b1" in requirements
    assert "opentelemetry-api==1.45.1" in billing_requirements
    assert "opentelemetry-sdk==1.45.1" in billing_requirements
    assert "opentelemetry-exporter-otlp-proto-grpc==1.45.1" in billing_requirements
    assert "opentelemetry-instrumentation-fastapi==0.66b1" in billing_requirements
    assert '"next": "15.5.28"' in web_package
    assert '"eslint-config-next": "15.5.28"' in web_package


def test_web_configuration_is_runtime_external() -> None:
    content = (REPO_ROOT / "web/Dockerfile").read_text(encoding="utf-8")
    assert "ARG NEXT_PUBLIC_" not in content
    assert "'libcrypto3>=3.5.8-r0' 'libssl3>=3.5.8-r0'" in content


def test_web_build_uses_non_secret_authentication_configuration() -> None:
    content = (REPO_ROOT / "web/Dockerfile").read_text(encoding="utf-8")
    build_stages, final_stage = content.rsplit("\nFROM node:", maxsplit=1)

    assert "KEYCLOAK_ISSUER=https://build.invalid/realms/waooaw" in build_stages
    assert "KEYCLOAK_EXPECTED_ISSUER=https://build.invalid/realms/waooaw" in build_stages
    assert "WAOOAW_SERVER_SESSION_MODE=enforced" in build_stages
    assert "KEYCLOAK_ISSUER=" not in final_stage
    assert "KEYCLOAK_EXPECTED_ISSUER=" not in final_stage
    assert "WAOOAW_SERVER_SESSION_MODE=" not in final_stage


def test_web_dependency_stage_copies_pnpm_patches_before_install() -> None:
    content = (REPO_ROOT / "web/Dockerfile").read_text(encoding="utf-8")
    patch_copy = "COPY web/patches ./patches"
    frozen_install = "RUN pnpm install --frozen-lockfile"

    assert patch_copy in content
    assert content.index(patch_copy) < content.index(frozen_install)


def test_baseline_excludes_oauth_vault_and_mcps() -> None:
    services = _compose()["services"]
    excluded = [name for name in services if name == "oauth-vault" or name.endswith("-mcp")]
    assert excluded == []


def test_ct01_uses_only_accepted_ce_port() -> None:
    compose_text = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "constitutional-engine:7000" not in compose_text
    assert "constitutional-engine:5002" in compose_text


def test_application_database_traffic_uses_pgbouncer() -> None:
    services = _compose()["services"]
    for member in (
        "constitutional-engine",
        "business-platform",
        "professional-runtime",
        "ai-runtime",
        "billing-engine",
    ):
        environment = services[member].get("environment", {})
        database_values = [
            str(value)
            for key, value in environment.items()
            if "ConnectionStrings" in key or key == "DATABASE_URL"
        ]
        assert database_values
        assert all("pgbouncer" in value and "5433" in value for value in database_values)


def test_temporal_has_health_gate_and_dependents_wait_for_it() -> None:
    services = _compose()["services"]
    temporal = services["temporal"]
    assert temporal["environment"]["DB"] == "postgres12"
    assert "hostname -i" in temporal["healthcheck"]["test"][-1]
    assert services["business-platform"]["depends_on"]["temporal"]["condition"] == "service_healthy"


def test_supporting_services_use_runnable_pinned_contracts() -> None:
    services = _compose()["services"]
    postgres_mounts = services["postgres"]["volumes"]
    assert len(postgres_mounts) == 2
    assert all(mount.endswith(":ro") for mount in postgres_mounts)
    assert any("01-schemas.sql" in mount for mount in postgres_mounts)
    assert any("02-users-and-permissions.sh" in mount for mount in postgres_mounts)

    pgbouncer = services["pgbouncer"]
    assert pgbouncer["image"] == "edoburu/pgbouncer:1.22.1-p0"
    assert pgbouncer["environment"]["LISTEN_PORT"] == 5433
    assert pgbouncer["environment"]["POOL_MODE"] == "transaction"

    keycloak = services["keycloak"]
    assert keycloak["environment"]["KC_HEALTH_ENABLED"] == "true"
    assert "KEYCLOAK_CLIENT_SECRET is required" in keycloak["environment"]["KEYCLOAK_CLIENT_SECRET"]
    assert "DEV_TEST_PASSWORD is required" in keycloak["environment"]["DEV_TEST_PASSWORD"]
    assert "127.0.0.1/9000" in keycloak["healthcheck"]["test"][-1]


def test_offline_member_health_contracts_match_runtime_listeners() -> None:
    services = _compose()["services"]
    business_platform = services["business-platform"]
    assert business_platform["environment"]["Keycloak__RequireHttpsMetadata"] == "false"
    assert business_platform["healthcheck"]["test"][-1].endswith("/health/ready")
    assert services["web"]["healthcheck"]["test"][-1] == "http://127.0.0.1:3000"


def test_no_blank_secret_defaults_in_release_members() -> None:
    services = _compose()["services"]
    for member in RELEASE_MEMBERS:
        for value in services[member].get("environment", {}).values():
            assert ":-changeme}" not in str(value)
            assert ":-placeholder" not in str(value)
            assert ":-stub}" not in str(value)
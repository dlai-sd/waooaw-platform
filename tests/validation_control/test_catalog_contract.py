"""WC102 validation catalog and dual-mode orchestration contracts."""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from validation_control.catalog_execution import (
    cleanup_command,
    compose_command,
    execution_command,
    runner_environment,
    select_plan_node,
    service_start_command,
    stage_input_directory,
)
from validation_control.candidate_controller import catalog_candidate_inputs
from validation_control.evidence_controller import BLOCKED_DEFERRED_AMENDMENT
from validation_control.orchestrator import (
    build_execution_plan,
    plan_execution_order,
    prerequisite_evidence_blockers,
    suppression_reason,
)


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "validation/engineering-validation.yaml"
SCHEMA_PATH = ROOT / "validation/catalog.schema.json"


def load_catalog() -> dict[str, object]:
    return yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))


def test_catalog_matches_schema_and_defines_every_referenced_gate() -> None:
    catalog = load_catalog()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    jsonschema.validate(catalog, schema)
    defined = set(catalog["gates"])
    referenced = set(catalog["full_gates"])
    for component in catalog["components"].values():
        referenced.update(component["gates"])

    assert referenced <= defined


def test_catalog_defines_complete_immutable_candidate_build_inputs() -> None:
    inputs = catalog_candidate_inputs(ROOT, load_catalog())

    assert inputs["required_images"] == set(load_catalog()["components"])
    assert inputs["required_gates"] == load_catalog()["full_gates"]
    assert inputs["generated_artifacts"]
    assert inputs["base_image_digests"]


def test_focused_and_qualification_modes_resolve_identical_commands() -> None:
    catalog = load_catalog()
    gate_ids = ["test-web", "test-python:professional-runtime"]

    focused = build_execution_plan(catalog, gate_ids, mode="focused", head_sha="a" * 40, run_id="focused-1")
    qualification = build_execution_plan(catalog, gate_ids, mode="qualification", head_sha="a" * 40, run_id="qualification-1")

    assert [node["command"] for node in focused["nodes"]] == [node["command"] for node in qualification["nodes"]]
    assert focused["authoritative"] is False
    assert qualification["requires_clean_commit"] is True
    assert focused["nodes"][0]["runner_manifest"].endswith("/typescript.json")
    assert focused["nodes"][0]["profile"] == "test-ts"
    assert focused["nodes"][0]["components"] == ["web"]


def test_plan_declares_machine_checkable_component_cost_and_evidence_graph() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(
        catalog,
        ["build:web", "test-web", "e2e:accessibility"],
        mode="focused",
        head_sha="a" * 40,
        run_id="graph",
    )
    by_gate = {node["gate_id"]: node for node in plan["nodes"]}

    assert plan["machine_checkable"] is True
    assert by_gate["build:web"]["owner"] == "web"
    assert by_gate["build:web"]["cost_class"] == "STATIC"
    assert by_gate["build:web"]["phase"] == "A_DESIGN"
    assert by_gate["build:web"]["direct_prerequisites"] == []
    assert by_gate["build:web"]["downstream_dependents"] == ["test-web"]
    assert by_gate["test-web"]["direct_prerequisites"] == ["build:web"]
    assert by_gate["test-web"]["phase"] == "B_COMPONENT"
    assert "web/**" in by_gate["test-web"]["invalidation_rule"]["changed_paths"]
    assert by_gate["test-web"]["acceptance_check"] == catalog["commands"]["test-web"]["shell"]
    assert by_gate["test-web"]["expected_evidence"]["artifacts"] == catalog["gates"]["test-web"]["artifacts"]
    assert by_gate["e2e:accessibility"]["owner"] == "validation-control"
    assert by_gate["e2e:accessibility"]["cost_class"] == "BROWSER"


def test_plan_uses_component_reverse_dependencies_as_direct_prerequisites() -> None:
    plan = build_execution_plan(
        load_catalog(),
        ["build:constitutional-engine", "build:business-platform"],
        mode="focused",
        head_sha="a" * 40,
        run_id="component-dependency",
    )

    assert plan["nodes"][1]["direct_prerequisites"] == ["build:constitutional-engine"]
    assert plan["nodes"][0]["downstream_dependents"] == ["build:business-platform"]


def test_full_plan_graph_is_acyclic_and_every_node_has_complete_contract() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(
        catalog,
        catalog["full_gates"],
        mode="qualification",
        head_sha="a" * 40,
        run_id="full-graph",
    )
    resolved: set[str] = set()

    while ready := [
        node for node in plan["nodes"] if node["gate_id"] not in resolved and set(node["direct_prerequisites"]) <= resolved
    ]:
        resolved.update(node["gate_id"] for node in ready)

    assert resolved == set(catalog["full_gates"])
    assert all(node["inputs"] and node["acceptance_check"] and node["expected_evidence"] for node in plan["nodes"])
    phase_order = {
        "A_DESIGN": 0,
        "B_COMPONENT": 1,
        "C_DEPENDENCY_INTEGRATION": 2,
        "D_SYSTEM_STITCHING": 3,
        "E_QUALIFICATION_HANDOFF": 4,
    }
    by_gate = {node["gate_id"]: node for node in plan["nodes"]}
    assert all(
        phase_order[by_gate[prerequisite]["phase"]] <= phase_order[node["phase"]]
        for node in plan["nodes"]
        for prerequisite in node["direct_prerequisites"]
    )
    ordered_nodes = [by_gate[gate_id] for gate_id in plan_execution_order(plan)]
    assert [phase_order[node["phase"]] for node in ordered_nodes] == sorted(phase_order[node["phase"]] for node in ordered_nodes)
    assert ordered_nodes[-1]["gate_id"] == "release-qualification"


def test_plan_rejects_duplicate_gate_chunks() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        build_execution_plan(
            load_catalog(),
            ["test-web", "test-web"],
            mode="focused",
            head_sha="a" * 40,
            run_id="duplicate",
        )


def test_plan_classifies_dependent_higher_cost_and_independent_suppression() -> None:
    plan = build_execution_plan(
        load_catalog(),
        ["build:web", "test-web", "e2e:accessibility", "build:constitutional-engine"],
        mode="focused",
        head_sha="a" * 40,
        run_id="suppression",
    )

    assert suppression_reason(plan, "test-web", "build:web") == "DEPENDENT_ON_FIRST_CAUSE"
    assert suppression_reason(plan, "e2e:accessibility", "build:web") == "HIGHER_COST_THAN_FIRST_CAUSE"
    assert suppression_reason(plan, "build:constitutional-engine", "build:web") is None


def test_prerequisite_evidence_blocks_missing_failed_and_forged_results() -> None:
    node = {"direct_prerequisites": ["acceptance:as-001"]}

    assert prerequisite_evidence_blockers(node, []) == ["missing:acceptance:as-001"]
    assert prerequisite_evidence_blockers(
        node,
        [{"gate_id": "acceptance:as-001", "result": "FAIL"}],
    ) == ["incompatible:acceptance:as-001:FAIL"]
    assert prerequisite_evidence_blockers(
        node,
        [
            {
                "gate_id": "acceptance:as-001",
                "result": "BLOCKED",
                "disposition": "BLOCKED-DEFERRED",
                "disposition_proof": {"founder_scope_amendment": "forged", "release_blocking": True},
            }
        ],
    ) == ["incompatible:acceptance:as-001:BLOCKED"]


def test_prerequisite_evidence_accepts_pass_and_exact_founder_deferral() -> None:
    assert (
        prerequisite_evidence_blockers(
            {"direct_prerequisites": ["build:web"]},
            [{"gate_id": "build:web", "result": "PASS"}],
        )
        == []
    )
    assert (
        prerequisite_evidence_blockers(
            {"direct_prerequisites": ["acceptance:as-001"]},
            [
                {
                    "gate_id": "acceptance:as-001",
                    "result": "BLOCKED",
                    "disposition": "BLOCKED-DEFERRED",
                    "disposition_proof": {
                        "founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT,
                        "release_blocking": True,
                    },
                }
            ],
        )
        == []
    )


def test_typescript_plan_uses_immutable_dependencies_outside_read_only_source() -> None:
    catalog = load_catalog()

    for gate_id in ("build:web", "test-web"):
        plan = build_execution_plan(catalog, [gate_id], mode="focused", head_sha="a" * 40, run_id=gate_id)
        command = plan["nodes"][0]["command"]
        assert "cp -a web /tmp/web" in command
        assert "ln -s /opt/waooaw-web/node_modules /tmp/web/node_modules" in command


def test_full_runner_is_limited_to_cross_stack_release_gates() -> None:
    catalog = load_catalog()

    full_runner_gates = {gate_id for gate_id, gate in catalog["gates"].items() if gate["runner_id"] == "full"}

    assert full_runner_gates == {
        "release-qualification",
        "spec-lint",
        "e2e:accessibility",
        "e2e:emergency-stop",
    }


def test_local_precheck_commands_are_catalog_owned_and_tool_pinned() -> None:
    root = Path(__file__).resolve().parents[2]
    catalog = load_catalog()

    assert {name: config["gate"] for name, config in catalog["prechecks"].items()} == {
        "gitleaks": "precheck:gitleaks",
        "scripts_quality": "quality:scripts",
        "dotnet_quality_business_platform": "quality:dotnet:business-platform",
        "typescript_quality": "quality:typescript",
        "business_platform": "test-dotnet:business-platform",
        "release_qualification": "release-qualification",
    }
    assert all(config["inputs"] for config in catalog["prechecks"].values())
    assert catalog["prechecks"]["gitleaks"]["always"] is True
    assert catalog["prechecks"]["business_platform"]["components"] == ["business-platform"]
    assert catalog["prechecks"]["release_qualification"]["gates"] == ["release-qualification"]
    assert "infrastructure/terraform/**" in catalog["prechecks"]["release_qualification"]["paths"]
    gitleaks = (root / "scripts/validation_control/run_gitleaks_gate.sh").read_text(encoding="utf-8")
    assert "zricethezav/gitleaks@sha256:" in gitleaks
    assert "zricethezav/gitleaks:v" not in gitleaks


def test_requirement_ledger_command_consumes_the_standard_changed_file_scope() -> None:
    catalog = load_catalog()

    assert catalog["commands"]["requirement-ledger"]["shell"] == (
        "python scripts/validate_requirement_ledger.py --repository-root /workspace "
        "--changed-file-list test-results/wc102/changed-files.txt"
    )


def test_concurrent_runs_receive_distinct_namespaces() -> None:
    catalog = load_catalog()

    first = build_execution_plan(catalog, ["test-web"], mode="focused", head_sha="a" * 40, run_id="one")
    second = build_execution_plan(catalog, ["test-web"], mode="focused", head_sha="a" * 40, run_id="two")

    assert first["execution_namespace"] != second["execution_namespace"]
    assert first["nodes"][0]["compose_project"] == first["execution_namespace"]
    assert second["nodes"][0]["compose_project"] == second["execution_namespace"]
    assert first["nodes"][0]["output_directory"] != second["nodes"][0]["output_directory"]
    assert first["nodes"][0]["output_directory"].endswith("/test-web")
    stable_fields = {"gate_id", "runner_id", "compose_service", "profile", "command_id", "command"}
    assert {field: first["nodes"][0][field] for field in stable_fields} == {
        field: second["nodes"][0][field] for field in stable_fields
    }


def test_catalog_gate_selection_controls_compose_execution() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(catalog, ["test-web"], mode="qualification", head_sha="a" * 40, run_id="hosted")

    node = select_plan_node(plan, "test-web")

    assert compose_command(node) == [
        "docker",
        "compose",
        "--project-name",
        plan["execution_namespace"],
        "--profile",
        "test-ts",
        "run",
        "--rm",
        "--pull",
        "never",
        "--volume",
        f"./{node['output_directory']}:/workspace/test-results",
        "test-runner-ts",
        "sh",
        "-lc",
        catalog["commands"]["test-web"]["shell"],
    ]


def test_catalog_gate_forwards_only_declared_environment() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(
        catalog,
        ["integration:multi-tenant"],
        mode="qualification",
        head_sha="a" * 40,
        run_id="integration",
    )

    node = select_plan_node(plan, "integration:multi-tenant")
    command = compose_command(node)

    assert node["runner_id"] == "dotnet"
    assert node["environment"] == ["DATABASE_URL", "TESTCONTAINERS_HOST_OVERRIDE"]
    assert node["required_services"] == ["postgres"]
    environment_position = command.index("-e")
    assert command[environment_position : environment_position + 2] == ["-e", "DATABASE_URL"]
    assert command[environment_position + 2 : environment_position + 4] == ["-e", "TESTCONTAINERS_HOST_OVERRIDE"]
    assert "/var/run/docker.sock:/var/run/docker.sock" in command

    assert service_start_command(node, "/usr/bin/docker") == [
        "/usr/bin/docker",
        "compose",
        "--project-name",
        plan["execution_namespace"],
        "--profile",
        "test-dotnet",
        "up",
        "--detach",
        "--no-build",
        "--pull",
        "missing",
        "--wait",
        "postgres",
    ]


def test_only_database_integration_gates_start_postgres() -> None:
    catalog = load_catalog()
    database_gates = {gate_id for gate_id, gate in catalog["gates"].items() if gate.get("required_services")}

    assert database_gates == {
        "integration:multi-tenant",
        "integration:postgres-migrations",
    }
    assert all(catalog["gates"][gate_id]["required_services"] == ["postgres"] for gate_id in database_gates)


def test_python_runner_database_url_matches_postgres_defaults() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert services["test-runner-python"]["environment"]["DATABASE_URL"] == (
        "postgresql://waooaw:${POSTGRES_PASSWORD:-waooaw-local-dev-only}@postgres:5432/waooaw"
    )
    assert services["postgres"]["environment"] == {
        "POSTGRES_USER": "waooaw",
        "POSTGRES_PASSWORD": "${POSTGRES_PASSWORD:-waooaw-local-dev-only}",
        "POSTGRES_DB": "waooaw",
    }
    assert services["postgres"]["image"] == (
        "pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b"
    )
    assert services["postgres"]["healthcheck"]["test"] == [
        "CMD-SHELL",
        'test "$(head -n 1 /var/lib/postgresql/data/postmaster.pid)" = 1 && pg_isready -U waooaw -d waooaw',
    ]


def test_multi_tenant_gate_runs_exact_http_and_postgres_rls_suites() -> None:
    catalog = load_catalog()
    command = (ROOT / "scripts/validation_control/run_multi_tenant_integration_gate.sh").read_text(encoding="utf-8")
    gate = catalog["gates"]["integration:multi-tenant"]

    assert "tests/business-platform.Tests/business-platform.Tests.csproj" in command
    assert "FullyQualifiedName~CCT_MT01_TenantIsolationTests" in command
    assert "FullyQualifiedName~TenantDbConnectionInterceptorPostgresTests" in command
    assert "cp -a /opt/nuget/packages/." in command
    assert "dotnet restore" in command
    assert "dotnet build" in command and "--no-restore" in command
    assert "dotnet test" in command and "--no-build" in command
    assert "trx;LogFileName=multi-tenant.trx" in command
    assert gate["resources"]["socket_classification"] == "testcontainers"


def test_postgres_migration_gate_verifies_fresh_service_initialization() -> None:
    command = (ROOT / "scripts/validation_control/run_postgres_migrations.sh").read_text(encoding="utf-8")

    assert 'psql "$DATABASE_URL" -v ON_ERROR_STOP=1' in command
    assert "infrastructure/postgres/init/*.sql" not in command
    assert "business.my_agents_selection_flash" in command
    assert "relation.relrowsecurity" in command
    assert "constitutional evidence grants violate append-only policy" in command
    assert "append-only rule inventory is incomplete" in command


def test_dotnet_integration_gate_runs_real_postgres_classes() -> None:
    catalog = load_catalog()
    command = (ROOT / "scripts/validation_control/run_dotnet_integration_gate.sh").read_text(encoding="utf-8")
    gate = catalog["gates"]["integration:dotnet"]

    assert "tests/business-platform.Tests/business-platform.Tests.csproj" in command
    assert "FullyQualifiedName~IntegrationTests|FullyQualifiedName~PostgresTests" in command
    assert "cp -a /opt/nuget/packages/." in command
    assert "dotnet build" in command and "--no-restore" in command
    assert "dotnet test" in command and "--no-build" in command
    assert "trx;LogFileName=dotnet-integration.trx" in command
    assert gate["environment"] == ["TESTCONTAINERS_HOST_OVERRIDE"]
    assert "required_services" not in gate
    assert gate["resources"]["socket_classification"] == "testcontainers"


def test_python_integration_gate_runs_real_cross_service_suites() -> None:
    catalog = load_catalog()
    command = (ROOT / "scripts/validation_control/run_python_integration_gate.sh").read_text(encoding="utf-8")
    gate = catalog["gates"]["integration:python"]

    assert "tests/professional-runtime/test_paas_runtime.py" in command
    assert "tests/professional-runtime/test_conversation_execution.py" in command
    assert "tests/ai-runtime/test_pse_router.py" in command
    assert "tests/trust-layer/test_ctg.py" in command
    assert "tests/integration/" not in command
    assert gate.get("environment", []) == []
    assert "required_services" not in gate


def test_seed_prompts_contract_executes_nonempty_synthetic_fixtures() -> None:
    command = (ROOT / "scripts/validation_control/run_seed_prompts_contract_gate.sh").read_text(encoding="utf-8")

    assert "pytest tests/scripts/test_seed_prompts.py" in command
    assert "seed-prompts.py --dry-run" not in command
    assert "--junitxml=test-results/seed-prompts-contract.xml" in command


def test_only_classified_gates_receive_the_docker_socket() -> None:
    catalog = load_catalog()
    classified = {gate_id for gate_id, gate in catalog["gates"].items() if gate["resources"]["docker_socket"] is True}

    assert classified == {
        "spec-lint",
        "release-qualification",
        "contract:rest",
        "integration:multi-tenant",
        "integration:dotnet",
        "test-dotnet:business-platform",
    }
    for gate_id in classified:
        resources = catalog["gates"][gate_id]["resources"]
        assert resources["socket_classification"] in {"nested-docker", "host-orchestration", "testcontainers"}
        plan = build_execution_plan(catalog, [gate_id], mode="focused", head_sha="a" * 40, run_id=gate_id)
        assert "/var/run/docker.sock:/var/run/docker.sock" in compose_command(plan["nodes"][0])


def test_catalog_gate_mounts_linked_worktree_git_directory_read_only() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(catalog, ["spec-lint"], mode="qualification", head_sha="a" * 40, run_id="git")

    command = compose_command(plan["nodes"][0], "/workspaces/repository/.git")

    assert "/workspaces/repository/.git:/workspaces/repository/.git:ro" in command


def test_disposable_project_cleanup_removes_namespaced_volumes() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(
        catalog,
        ["build:constitutional-engine"],
        mode="focused",
        head_sha="a" * 40,
        run_id="cleanup",
    )
    node = plan["nodes"][0]

    assert node["output_directory"].endswith("/build-constitutional-engine")
    assert cleanup_command(node, "/usr/bin/docker") == [
        "/usr/bin/docker",
        "compose",
        "--project-name",
        plan["execution_namespace"],
        "down",
        "--volumes",
        "--remove-orphans",
    ]


def test_catalog_gate_forwards_docker_socket_group(tmp_path: Path) -> None:
    docker_socket = tmp_path / "docker.sock"
    docker_socket.touch()

    environment = runner_environment("sha256:" + "a" * 64, docker_socket)

    assert environment["DOCKER_GID"] == str(docker_socket.stat().st_gid)


def test_hosted_inputs_are_mirrored_inside_isolated_artifact_root(tmp_path: Path) -> None:
    source = tmp_path / "test-results/wc104/c065"
    source.mkdir(parents=True)
    (source / "base-sha.txt").write_text("b" * 40 + "\n", encoding="utf-8")
    artifact_root = tmp_path / "test-results/wc109/runs/hosted/author-review-gate"
    artifact_root.mkdir(parents=True)

    target = stage_input_directory(tmp_path, Path("test-results/wc104/c065"), artifact_root)

    assert target == artifact_root / "wc104/c065"
    assert (target / "base-sha.txt").read_text(encoding="utf-8") == "b" * 40 + "\n"

    (target / "stale.txt").write_text("stale\n", encoding="utf-8")
    (source / "base-sha.txt").write_text("c" * 40 + "\n", encoding="utf-8")
    stage_input_directory(tmp_path, Path("test-results/wc104/c065"), artifact_root)

    assert (target / "base-sha.txt").read_text(encoding="utf-8") == "c" * 40 + "\n"
    assert not (target / "stale.txt").exists()


def test_hosted_input_staging_rejects_paths_outside_test_results(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    artifact_root = tmp_path / "test-results/wc109/runs/hosted/gate"
    artifact_root.mkdir(parents=True)

    with pytest.raises(ValueError, match="below test-results"):
        stage_input_directory(tmp_path, outside, artifact_root)


def test_python_builds_write_bytecode_only_to_disposable_state() -> None:
    catalog = load_catalog()

    for command_id in (
        "build-professional-runtime",
        "build-ai-runtime",
        "build-billing-engine",
        "build-agent-adapter",
    ):
        command = catalog["commands"][command_id]["shell"]
        assert command.startswith("PYTHONPYCACHEPREFIX=/tmp/pycache/")
        assert "python -m compileall -q src/" in command


def test_dotnet_builds_restore_and_build_in_the_same_disposable_artifact_path() -> None:
    catalog = load_catalog()

    for command_id, service in (
        ("build-constitutional-engine", "constitutional-engine"),
        ("build-business-platform", "business-platform"),
    ):
        command = catalog["commands"][command_id]["shell"]
        artifact_path = f"--artifacts-path /tmp/artifacts/{service}"
        assert command.count(artifact_path) == 2
        assert "dotnet restore" in command
        assert "dotnet build" in command
        assert command.endswith("--no-restore")


def test_dotnet_mutation_thresholds_match_pinned_stryker_cli() -> None:
    source = (Path(__file__).resolve().parents[2] / "scripts/validation_control/run_dotnet_mutation_gate.sh").read_text()

    assert "--threshold-high 80 --threshold-low 75 --break-at 65" in source
    assert "--threshold-break" not in source
    assert "tests/constitutional-engine.Tests" in source
    assert 'cd "$worktree/tests/constitutional-engine.Tests"' in source
    assert "--project constitutional-engine.csproj" in source


def test_host_orchestration_declares_whether_it_consumes_a_runner() -> None:
    catalog = load_catalog()
    release = build_execution_plan(
        catalog,
        ["release-qualification"],
        mode="qualification",
        head_sha="a" * 40,
        run_id="release",
    )["nodes"][0]
    gitleaks = build_execution_plan(
        catalog,
        ["precheck:gitleaks"],
        mode="qualification",
        head_sha="a" * 40,
        run_id="precheck",
    )["nodes"][0]

    assert release["execution"] == "host" and release["runner_required"] is True
    assert gitleaks["execution"] == "host" and gitleaks["runner_required"] is False


def test_rest_contract_declares_product_builds_and_isolated_host_orchestration() -> None:
    catalog = load_catalog()
    node = build_execution_plan(
        catalog,
        ["contract:rest"],
        mode="focused",
        head_sha="a" * 40,
        run_id="rest-contract",
    )["nodes"][0]

    assert node["execution"] == "host"
    assert node["product_image_builds"] == ["business-platform", "professional-runtime"]
    assert node["compose_project"].startswith("wc109-")


def test_catalog_gate_selection_rejects_missing_or_duplicate_nodes() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(catalog, ["test-web"], mode="focused", head_sha="a" * 40, run_id="hosted")

    with pytest.raises(ValueError, match="exactly one"):
        select_plan_node(plan, "test-python")

    plan["nodes"].append(plan["nodes"][0])
    with pytest.raises(ValueError, match="exactly one"):
        select_plan_node(plan, "test-web")


def test_release_qualification_is_explicit_host_orchestration() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(
        catalog,
        ["release-qualification"],
        mode="qualification",
        head_sha="a" * 40,
        run_id="release",
    )
    node = select_plan_node(plan, "release-qualification")

    assert node["runner_id"] == "full"
    assert node["execution"] == "host"
    assert execution_command(node, "/usr/bin/docker") == [
        "sh",
        "-lc",
        "sh scripts/run_release_qualification.sh",
    ]

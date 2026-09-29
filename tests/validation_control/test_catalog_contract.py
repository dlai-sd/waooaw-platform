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
)
from validation_control.orchestrator import build_execution_plan


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

    assert node["environment"] == ["DATABASE_URL"]
    environment_position = command.index("-e")
    assert command[environment_position : environment_position + 2] == ["-e", "DATABASE_URL"]
    assert "/var/run/docker.sock:/var/run/docker.sock" not in command


def test_only_classified_gates_receive_the_docker_socket() -> None:
    catalog = load_catalog()
    classified = {gate_id for gate_id, gate in catalog["gates"].items() if gate["resources"]["docker_socket"] is True}

    assert classified == {"spec-lint", "release-qualification", "contract:rest"}
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

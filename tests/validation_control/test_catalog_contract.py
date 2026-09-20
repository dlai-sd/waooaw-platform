"""WC102 validation catalog and dual-mode orchestration contracts."""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from validation_control.catalog_execution import compose_command, execution_command, select_plan_node
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

    assert catalog["prechecks"] == {
        "gitleaks": {"always": True, "gate": "precheck:gitleaks"},
        "business_platform": {"components": ["business-platform"], "gate": "test-dotnet:business-platform"},
        "release_qualification": {"gates": ["release-qualification"], "gate": "release-qualification"},
    }
    gitleaks = (root / "scripts/validation_control/run_gitleaks_gate.sh").read_text(encoding="utf-8")
    assert "zricethezav/gitleaks@sha256:" in gitleaks
    assert "zricethezav/gitleaks:v" not in gitleaks


def test_concurrent_runs_receive_distinct_namespaces() -> None:
    catalog = load_catalog()

    first = build_execution_plan(catalog, ["test-web"], mode="focused", head_sha="a" * 40, run_id="one")
    second = build_execution_plan(catalog, ["test-web"], mode="focused", head_sha="a" * 40, run_id="two")

    assert first["execution_namespace"] != second["execution_namespace"]
    assert first["nodes"] == second["nodes"]


def test_catalog_gate_selection_controls_compose_execution() -> None:
    catalog = load_catalog()
    plan = build_execution_plan(catalog, ["test-web"], mode="qualification", head_sha="a" * 40, run_id="hosted")

    node = select_plan_node(plan, "test-web")

    assert compose_command(node) == [
        "docker",
        "compose",
        "--profile",
        "test-ts",
        "run",
        "--rm",
        "--pull",
        "never",
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
    assert command[command.index("--pull") + 2 : command.index("test-runner-python")] == ["-e", "DATABASE_URL"]


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

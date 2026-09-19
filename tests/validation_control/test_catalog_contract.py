"""WC102 validation catalog and dual-mode orchestration contracts."""

import json
from pathlib import Path

import jsonschema
import yaml

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

    focused = build_execution_plan(catalog, gate_ids, mode="focused", head_sha="a" * 40)
    qualification = build_execution_plan(catalog, gate_ids, mode="qualification", head_sha="a" * 40)

    assert [node["command"] for node in focused["nodes"]] == [node["command"] for node in qualification["nodes"]]
    assert focused["authoritative"] is False
    assert qualification["requires_clean_commit"] is True

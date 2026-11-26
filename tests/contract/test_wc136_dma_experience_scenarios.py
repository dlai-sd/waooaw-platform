"""WC-136 C6-06: DMA experience scenarios, adapter contract carries `experience`, compatibility tuple pins 1.2.0."""

# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-06
# Constitutional basis: C-059, C-063, ADR-051

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/agent-adapters"))

from runtime_contract.employment import EmploymentInterfaceManifest  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/wc136/dma-experience-scenarios.yaml"
ADAPTER_SPEC = ROOT / "architecture/reference/api-specs/conversational-employment-domain-adapter.openapi.yaml"
TUPLE = ROOT / "src/digital-marketing-agent/contracts/compatibility-tuple.v1.json"
SCENARIOS = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _manifest() -> dict[str, Any]:
    return json.loads((ROOT / SCENARIOS["manifest"]).read_text(encoding="utf-8"))


def _apply(document: dict[str, Any], change: dict[str, Any]) -> None:
    if change["op"] == "none":
        return
    parent: Any = document
    for step in change["path"][:-1]:
        parent = parent[step]
    leaf = change["path"][-1]
    if change["op"] == "remove":
        del parent[leaf]
    else:
        parent[leaf] = change["value"]


def test_c6_06_scenarios_are_unique_and_use_known_outcomes() -> None:
    identifiers = [item["scenarioId"] for item in SCENARIOS["scenarios"]]

    assert len(identifiers) == len(set(identifiers))
    assert {item["expect"]["state"] for item in SCENARIOS["scenarios"]} == {
        "COMPATIBLE",
        "NOT_DECLARED",
        "INCOMPATIBLE",
    }


@pytest.mark.parametrize("scenario", SCENARIOS["scenarios"], ids=lambda item: item["scenarioId"])
def test_c6_06_python_manifest_model_agrees_with_each_scenario(scenario: dict[str, Any]) -> None:
    document = copy.deepcopy(_manifest())
    _apply(document, scenario["change"])

    if scenario["expect"]["pythonModelValid"]:
        EmploymentInterfaceManifest.model_validate(document)
    else:
        with pytest.raises(ValidationError):
            EmploymentInterfaceManifest.model_validate(document)


def test_c6_06_adapter_contract_declares_the_optional_experience_section() -> None:
    spec = yaml.safe_load(ADAPTER_SPEC.read_text(encoding="utf-8"))
    schemas = spec["components"]["schemas"]
    manifest = schemas["EmploymentInterfaceManifestV1"]

    assert manifest["properties"]["experience"] == {"$ref": "#/components/schemas/EmploymentExperienceManifestV1"}
    assert "experience" not in manifest["required"]
    experience = schemas["EmploymentExperienceManifestV1"]
    assert experience["additionalProperties"] is False
    assert set(experience["required"]) >= {"contractVersion", "goalTypes", "operate", "monitor", "components"}
    for reference in ("EmploymentExperienceBlockTypeV1", "EmploymentExperienceComponentV1"):
        assert reference in schemas


def test_c6_06_compatibility_tuple_pins_the_published_manifest_version() -> None:
    assert json.loads(TUPLE.read_text(encoding="utf-8"))["manifestVersion"] == _manifest()["manifestVersion"] == "1.2.0"

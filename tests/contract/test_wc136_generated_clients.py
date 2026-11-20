"""WC-136 C2-06: the generated TypeScript clients match the Workbench and Pricing Admin specifications."""

# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-06
# Constitutional basis: C-023, C-059, C-065

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "architecture/reference/api-specs"
GENERATED = ROOT / "web/lib/api/generated"
SCRIPT = ROOT / "scripts/generate_wc136_clients.sh"
BUNDLER = ROOT / "scripts/validation_control/bundle_wc136_openapi.py"

SLICES = {
    "workbench-v1": "agent-experience-workbench.openapi.yaml",
    "pricing-admin-v1": "pricing-admin-business-platform.openapi.yaml",
}


def _spec(name: str) -> dict:
    return yaml.safe_load((API / name).read_text(encoding="utf-8"))


def _tags(spec: dict) -> set[str]:
    return {
        tag
        for item in spec["paths"].values()
        for operation in item.values()
        if isinstance(operation, dict)
        for tag in operation.get("tags", [])
    }


def test_wc136_r010_script_pins_the_generator_and_bundles_both_slices() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "openapitools/openapi-generator-cli:v7.17.0" in text
    assert "bundle_wc136_openapi.py" in text
    for name in SLICES.values():
        assert name in text
    assert "@waooaw/workbench-client" in text and "@waooaw/pricing-admin-client" in text
    assert BUNDLER.is_file()


@pytest.mark.parametrize(("directory", "spec_name"), sorted(SLICES.items()))
def test_wc136_r010_generated_client_has_an_api_per_tag_and_a_model_per_schema(
    directory: str, spec_name: str
) -> None:
    spec = _spec(spec_name)
    apis = {path.stem for path in (GENERATED / directory / "src/apis").glob("*Api.ts")}
    expected = {re.sub(r"[^A-Za-z0-9]", "", tag) + "Api" for tag in _tags(spec)}
    assert expected <= apis
    models = {path.stem for path in (GENERATED / directory / "src/models").glob("*.ts")}
    local_schemas = set(spec["components"]["schemas"])
    assert local_schemas
    assert all(name in models for name in local_schemas)


@pytest.mark.parametrize(("directory", "spec_name"), sorted(SLICES.items()))
def test_wc136_r010_generation_manifest_binds_the_specification_digest(
    directory: str, spec_name: str
) -> None:
    manifest = json.loads((GENERATED / directory / "generation-manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256((API / spec_name).read_bytes()).hexdigest()
    assert manifest["generatorImage"] == "openapitools/openapi-generator-cli:v7.17.0"
    assert manifest["specSha256"] == digest

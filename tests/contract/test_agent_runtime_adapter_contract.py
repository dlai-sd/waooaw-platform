"""WC-080 machine-contract and private-route conformance."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §9
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
ADAPTER_SCHEMA = json.loads(
    (ROOT / "architecture/reference/api-specs/schemas/agent-runtime-adapter-v1.schema.json").read_text()
)
ADMISSION_SCHEMA = json.loads(
    (ROOT / "architecture/reference/api-specs/schemas/agent-admission-contract-v1.schema.json").read_text()
)
ADMISSION_FIXTURES = [
    ROOT / "tests/fixtures/agent-admission/digital-marketing-local-service-v3.1.0.json",
    ROOT / "tests/fixtures/agent-admission/trading-fo-crypto-v1.8.0.json",
]


@pytest.mark.parametrize("fixture_path", ADMISSION_FIXTURES)
def test_admission_requires_exact_runtime_adapter_binding(fixture_path: Path) -> None:
    contract = json.loads(fixture_path.read_text())
    jsonschema.Draft202012Validator(ADMISSION_SCHEMA).validate(contract)

    missing = copy.deepcopy(contract)
    del missing["runtimeAdapter"]
    forged = copy.deepcopy(contract)
    forged["runtimeAdapter"]["artifactDigest"] = "latest"
    unsupported = copy.deepcopy(contract)
    unsupported["runtimeAdapter"]["protocolVersion"] = "2.0.0"

    for invalid in (missing, forged, unsupported):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(ADMISSION_SCHEMA).validate(invalid)


def test_adapter_schema_defines_strict_normative_types() -> None:
    required = {
        "AdapterDescriptorV1",
        "AdapterInvocationEnvelopeV1",
        "AdapterOperationRequestV1",
        "AdapterInvocationV1",
        "AdapterEventV1",
        "AdapterResultV1",
        "ProblemDetail",
    }
    assert required <= ADAPTER_SCHEMA["$defs"].keys()
    assert all(ADAPTER_SCHEMA["$defs"][name]["additionalProperties"] is False for name in required)


def test_openapi_operations_have_exact_pr_only_route_grants() -> None:
    spec = yaml.safe_load(
        (ROOT / "architecture/reference/api-specs/agent-runtime-adapter-v1.openapi.yaml").read_text()
    )
    registry = yaml.safe_load((ROOT / "infrastructure/workload-identity/registry.yaml").read_text())
    targets = {"agent-runtime-adapter-digital-marketing", "agent-runtime-adapter-trading"}

    protected_operations = {
        (method.upper(), path, operation["operationId"])
        for path, path_item in spec["paths"].items()
        for method, operation in path_item.items()
        if method in {"get", "post"} and path != "/health/live"
    }
    grants = {
        (grant["target"], grant["method"], grant["route"], grant["operation"])
        for grant in registry["route_grants"]
        if grant["target"] in targets
    }

    assert grants == {
        (target, method, path, operation)
        for target in targets
        for method, path, operation in protected_operations
    }
    assert all(grant["caller"] == "professional-runtime" for grant in registry["route_grants"] if grant["target"] in targets)
    assert {"demo", "uat", "prod"} <= registry["environments"].keys()
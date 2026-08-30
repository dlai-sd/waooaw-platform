"""WC-079 Agent Admission Contract compatibility fixtures."""

# Implements: WC-079 AA-02, AA-10, AA-11
# constitutional_basis: C-032, C-036, C-037, C-059, C-063, C-094

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "architecture/reference/api-specs/schemas/agent-admission-contract-v1.schema.json").read_text())
FIXTURES = [
    ROOT / "tests/fixtures/agent-admission/digital-marketing-local-service-v3.1.0.json",
    ROOT / "tests/fixtures/agent-admission/trading-fo-crypto-v1.8.0.json",
]
SPEC_DIGESTS = {
    "DIGITAL_MARKETING_LOCAL_SERVICE": "128b39b26346e5d09047e8cc835a3e3e6c7e627386d5ce9ad0df7e17c13a4ea2",
    "TRADING_FO_CRYPTO": "10aaff0fa8c8fec8ec5becce8e85255ce43e0d0c7202c396aea26c28d07ce450",
}


@pytest.mark.parametrize("fixture_path", FIXTURES)
def test_frozen_professional_uses_shared_strict_schema(fixture_path: Path) -> None:
    contract = json.loads(fixture_path.read_text())

    jsonschema.Draft202012Validator(SCHEMA).validate(contract)

    identity = contract["professionalIdentity"]
    specification = ROOT / identity["agentSpecification"]["path"]
    assert hashlib.sha256(specification.read_bytes()).hexdigest() == SPEC_DIGESTS[identity["professionalTypeId"]]
    assert identity["agentSpecification"]["digest"] == f"sha256:{SPEC_DIGESTS[identity['professionalTypeId']]}"


def test_multi_skill_and_materially_different_cadence_are_preserved() -> None:
    digital, trading = [json.loads(path.read_text()) for path in FIXTURES]

    assert len(digital["skillManifest"]) > 1
    assert trading["skillManifest"][0]["schedulePolicy"]["mode"] == "EVENT_DRIVEN"
    assert trading["skillManifest"][0]["reviewPolicy"]["performanceReviewDays"] != 30
    assert {tuple(item["professionalIdentity"]["supportedChannels"]) for item in (digital, trading)} == {
        ("WEB", "WHATSAPP"),
        ("WEB", "API"),
    }


def test_unknown_or_missing_contract_fields_fail() -> None:
    contract = json.loads(FIXTURES[0].read_text())
    unknown = copy.deepcopy(contract)
    unknown["submitterReadiness"] = "PASS"
    missing = copy.deepcopy(contract)
    del missing["complianceDeclaration"]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(unknown)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(SCHEMA).validate(missing)
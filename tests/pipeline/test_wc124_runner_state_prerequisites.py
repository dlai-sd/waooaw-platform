"""WC-124 ADR-047 runner and isolated state prerequisite contracts."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §9.2
# Constitutional basis: C-023, C-059, C-065, C-066, C-080

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
STACK = ROOT / "infrastructure/deployment-stacks/goal006-runner"
CONTRACT = ROOT / "work-contracts/WC-124-runner-state-prerequisites.yaml"


def parameter(environment: str, name: str) -> str:
    document = json.loads((STACK / f"{environment}.parameters.json").read_text(encoding="utf-8"))
    return document["parameters"][name]["value"]


def test_demo_and_uat_have_distinct_exact_state_ownership() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    demo = contract["environments"]["demo"]
    uat = contract["environments"]["uat"]

    assert demo["state_storage_account"] == "waooawp3tfstate2ed118"
    assert uat["state_storage_account"] == "waooawuatstate2ed118"
    assert demo["state_storage_account"] != uat["state_storage_account"]
    for environment, record in contract["environments"].items():
        state_id = parameter(environment, "stateStorageAccountId")
        assert state_id.endswith(f"/storageAccounts/{record['state_storage_account']}")
        assert record["foundation_backend_key"] == f"goal006/{environment}/foundation.tfstate"
        assert record["workload_backend_key"] == f"goal006/{environment}/workload.tfstate"


def test_roots_bind_exact_backend_keys_and_oidc_without_public_fallback() -> None:
    for environment in ("demo", "uat"):
        for root in ("foundation", "workload"):
            source = (
                ROOT
                / f"infrastructure/terraform/phase2/environments/{environment}/{root}/main.tf"
            ).read_text(encoding="utf-8")
            assert f'key = "goal006/{environment}/{root}.tfstate"' in source
            assert "use_oidc" in source
            if root == "workload":
                assert "use_azuread_auth" in source
            assert "client_secret" not in source.lower()
            assert "public_network_access" not in source


def test_live_exit_contract_remains_fail_closed_until_separately_authorized() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))

    assert contract["repository_contract_status"] == "IMPLEMENTED"
    assert contract["live_evidence_status"] == "REQUIRED_NOT_YET_AUTHORIZED"
    assert len(contract["mandatory_live_oracles"]) == 9
    assert set(contract["authorization"].values()) == {
        "authorized",
        "not_authorized",
    }
    assert contract["authorization"]["azure_plan"] == "not_authorized"
    assert contract["authorization"]["azure_apply"] == "not_authorized"
    assert contract["dependency"]["blocks"] == "PST-WC04_ACCEPTANCE"


def test_environment_subjects_are_exact_and_non_interchangeable() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    subjects = {
        record["oidc_subject"]
        for record in contract["environments"].values()
    }
    assert subjects == {
        "repo:dlai-sd/waooaw-platform:environment:demo",
        "repo:dlai-sd/waooaw-platform:environment:uat",
    }
    assert all(
        re.fullmatch(
            r"repo:dlai-sd/waooaw-platform:environment:(demo|uat)",
            subject,
        )
        for subject in subjects
    )

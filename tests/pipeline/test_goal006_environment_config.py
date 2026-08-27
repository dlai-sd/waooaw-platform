import json
from pathlib import Path

import pytest

from scripts.goal006_environment_config import resolve_environment_config


def _write_environment(
    root: Path,
    environment: str,
    activation_state: str,
    *,
    control_plane_client_id: str | None = "control-client",
    cleanup_client_id: str | None = "cleanup-client",
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{environment}.parameters.json").write_text(
        json.dumps(
            {
                "parameters": {
                    "activationState": {"value": activation_state},
                    "runnerResourceGroupName": {"value": f"waooaw-{environment}-runner-rg"},
                    "stateStorageAccountId": {
                        "value": "/subscriptions/sub/resourceGroups/state/providers/"
                        "Microsoft.Storage/storageAccounts/stateaccount"
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    identities_path = root / "deployment-identities.json"
    identities = json.loads(identities_path.read_text(encoding="utf-8")) if identities_path.exists() else {}
    identities[environment] = {
        "control_plane_client_id": control_plane_client_id,
        "cleanup_client_id": cleanup_client_id,
    }
    identities_path.write_text(json.dumps(identities), encoding="utf-8")


def test_active_environment_resolves_all_environment_scoped_values(tmp_path: Path) -> None:
    _write_environment(tmp_path, "demo", "ACTIVE")

    config = resolve_environment_config("demo", stack_root=tmp_path)

    assert config["runner_resource_group"] == "waooaw-demo-runner-rg"
    assert config["runner_broker_job"] == "goal006-demo-runner-broker"
    assert config["runner_cleanup_broker_job"] == "goal006-demo-runner-cleanup"
    assert config["runner_job"] == "goal006-demo-runner-job"
    assert config["runner_label"] == "goal006-demo-private"
    assert config["runner_virtual_network_id"] == (
        "/subscriptions/sub/resourceGroups/waooaw-demo-runner-rg/providers/"
        "Microsoft.Network/virtualNetworks/goal006-demo-runner-vnet"
    )
    assert config["state_storage_account"] == "stateaccount"
    assert config["cleanup_evidence_container"] == "goal006-demo-runner-evidence"


@pytest.mark.parametrize("environment", ["uat", "prod"])
def test_inactive_environment_fails_before_deployment(tmp_path: Path, environment: str) -> None:
    _write_environment(tmp_path, environment, "INACTIVE", control_plane_client_id=None, cleanup_client_id=None)

    with pytest.raises(ValueError, match="deployment is not ready"):
        resolve_environment_config(environment, stack_root=tmp_path)


def test_active_environment_requires_complete_identities(tmp_path: Path) -> None:
    _write_environment(tmp_path, "demo", "ACTIVE", cleanup_client_id=None)

    with pytest.raises(ValueError, match="identities are incomplete"):
        resolve_environment_config("demo", stack_root=tmp_path)


def test_inactive_environment_can_be_inspected_without_identities(tmp_path: Path) -> None:
    _write_environment(tmp_path, "uat", "INACTIVE", control_plane_client_id=None, cleanup_client_id=None)

    config = resolve_environment_config("uat", stack_root=tmp_path, require_active=False)

    assert config["activation_state"] == "INACTIVE"
    assert config["control_plane_client_id"] == ""


def test_environment_config_rejects_unknown_environment(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="environment"):
        resolve_environment_config("invalid", stack_root=tmp_path)


def test_environment_config_requires_identity_record(tmp_path: Path) -> None:
    _write_environment(tmp_path, "demo", "ACTIVE")
    (tmp_path / "deployment-identities.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="identities are missing"):
        resolve_environment_config("demo", stack_root=tmp_path)


def test_environment_config_requires_parameter_value(tmp_path: Path) -> None:
    _write_environment(tmp_path, "demo", "ACTIVE")
    parameters_path = tmp_path / "demo.parameters.json"
    parameters = json.loads(parameters_path.read_text(encoding="utf-8"))
    parameters["parameters"].pop("runnerResourceGroupName")
    parameters_path.write_text(json.dumps(parameters), encoding="utf-8")

    with pytest.raises(ValueError, match="runnerResourceGroupName"):
        resolve_environment_config("demo", stack_root=tmp_path)


def test_environment_config_requires_storage_resource_id(tmp_path: Path) -> None:
    _write_environment(tmp_path, "demo", "ACTIVE")
    parameters_path = tmp_path / "demo.parameters.json"
    parameters = json.loads(parameters_path.read_text(encoding="utf-8"))
    parameters["parameters"]["stateStorageAccountId"]["value"] = "stateaccount"
    parameters_path.write_text(json.dumps(parameters), encoding="utf-8")

    with pytest.raises(ValueError, match="Storage account resource ID"):
        resolve_environment_config("demo", stack_root=tmp_path)
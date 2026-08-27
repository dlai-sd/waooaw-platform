#!/usr/bin/env python3
"""Resolve environment-scoped GOAL-006 deployment configuration."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


STACK_ROOT = Path("infrastructure/deployment-stacks/goal006-runner")


def _parameter(parameters: Mapping[str, Any], name: str) -> Any:
    value = parameters.get(name)
    if not isinstance(value, Mapping) or "value" not in value:
        raise ValueError(f"runner parameter {name} is missing")
    return value["value"]


def resolve_environment_config(
    environment: str,
    *,
    stack_root: Path = STACK_ROOT,
    require_active: bool = True,
) -> dict[str, str]:
    if environment not in {"demo", "uat", "prod"}:
        raise ValueError("environment must be demo, uat, or prod")

    parameter_path = stack_root / f"{environment}.parameters.json"
    identities_path = stack_root / "deployment-identities.json"
    parameters = json.loads(parameter_path.read_text(encoding="utf-8"))["parameters"]
    identities = json.loads(identities_path.read_text(encoding="utf-8"))
    activation_state = _parameter(parameters, "activationState")
    if require_active and activation_state != "ACTIVE":
        raise ValueError(
            f"{environment} deployment is not ready: private runner activation state is {activation_state}"
        )

    identity = identities.get(environment)
    if not isinstance(identity, Mapping):
        raise ValueError(f"deployment identities are missing for {environment}")
    control_plane_client_id = identity.get("control_plane_client_id")
    cleanup_client_id = identity.get("cleanup_client_id")
    if require_active and (not control_plane_client_id or not cleanup_client_id):
        raise ValueError(f"deployment identities are incomplete for active environment {environment}")

    state_storage_account_id = _parameter(parameters, "stateStorageAccountId")
    if not isinstance(state_storage_account_id, str) or "/storageAccounts/" not in state_storage_account_id:
        raise ValueError("stateStorageAccountId must be an Azure Storage account resource ID")
    state_storage_account = state_storage_account_id.rsplit("/", 1)[-1]
    runner_resource_group = str(_parameter(parameters, "runnerResourceGroupName"))

    return {
        "environment": environment,
        "activation_state": str(activation_state),
        "control_plane_client_id": str(control_plane_client_id or ""),
        "cleanup_client_id": str(cleanup_client_id or ""),
        "runner_resource_group": runner_resource_group,
        "runner_broker_job": f"goal006-{environment}-runner-broker",
        "runner_cleanup_broker_job": f"goal006-{environment}-runner-cleanup",
        "runner_job": f"goal006-{environment}-runner-job",
        "runner_label": f"goal006-{environment}-private",
        "state_storage_account_id": state_storage_account_id,
        "state_storage_account": state_storage_account,
        "cleanup_evidence_container": f"goal006-{environment}-runner-evidence",
    }


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--stack-root", type=Path, default=STACK_ROOT)
    parser.add_argument("--allow-inactive", action="store_true")
    arguments = parser.parse_args()
    print(
        json.dumps(
            resolve_environment_config(
                arguments.environment,
                stack_root=arguments.stack_root,
                require_active=not arguments.allow_inactive,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
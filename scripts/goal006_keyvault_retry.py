#!/usr/bin/env python3
"""Classify retryable Key Vault managed-identity propagation failures."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

MANAGED_IDENTITY_FAILURE = "Unable to get value using Managed identity"
KEY_VAULT_SECRET_PATH = re.compile(r"/secrets/([^/]+)", re.IGNORECASE)


def _names_secret_in_failure(apply_log: str, name: str) -> bool:
    return any(
        marker in apply_log
        for marker in (
            f"for secret {name}",
            f"for secret '{name}'",
            f'for secret "{name}"',
            f'Invalid value: \\"{name}\\"',
            f'Invalid value: "{name}"',
        )
    )


def _planned_container_app_secret_names(plan: object) -> set[str]:
    if not isinstance(plan, dict):
        return set()
    planned_values = plan.get("planned_values")
    if not isinstance(planned_values, dict):
        return set()
    root_module = planned_values.get("root_module")
    if not isinstance(root_module, dict):
        return set()

    names: set[str] = set()
    pending = [root_module]
    while pending:
        module = pending.pop()
        child_modules = module.get("child_modules", [])
        if isinstance(child_modules, list):
            pending.extend(child for child in child_modules if isinstance(child, dict))
        resources = module.get("resources", [])
        if not isinstance(resources, list):
            continue
        for resource in resources:
            if not isinstance(resource, dict) or resource.get("type") != "azurerm_container_app":
                continue
            values = resource.get("values")
            if not isinstance(values, dict):
                continue
            secrets = values.get("secret", [])
            if not isinstance(secrets, list):
                continue
            for secret in secrets:
                if not isinstance(secret, dict):
                    continue
                secret_id = secret.get("key_vault_secret_id")
                if not isinstance(secret_id, str):
                    continue
                match = KEY_VAULT_SECRET_PATH.search(secret_id)
                if match:
                    names.add(match.group(1))
    return names


def is_retryable(apply_log: str, inventory: object, plan: object | None = None) -> bool:
    names = _planned_container_app_secret_names(plan)
    if isinstance(inventory, dict) and isinstance(inventory.get("credentials"), list):
        names.update(
            credential["name"]
            for credential in inventory["credentials"]
            if isinstance(credential, dict) and isinstance(credential.get("name"), str)
        )
    return MANAGED_IDENTITY_FAILURE in apply_log and any(_names_secret_in_failure(apply_log, name) for name in names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-log", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    arguments = parser.parse_args()

    try:
        apply_log = arguments.apply_log.read_text(encoding="utf-8")
        inventory = json.loads(arguments.inventory.read_text(encoding="utf-8"))
        plan = json.loads(arguments.plan.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 1
    return 0 if is_retryable(apply_log, inventory, plan) else 1


if __name__ == "__main__":
    raise SystemExit(main())

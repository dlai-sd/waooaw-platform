"""Fail closed when a GOAL-006 foundation plan would destroy resources."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


KNOWN_ACTIONS = frozenset({"no-op", "create", "read", "update", "delete"})
TEMPORAL_ADDRESS = "module.workload.azurerm_container_app.temporal[0]"
TEMPORAL_ROLE_ADDRESS = "module.workload.azurerm_role_assignment.temporal_secret[0]"
LEGACY_TEMPORAL_SCOPE_SUFFIX = "/secrets/business-platform"
DATABASE_TEMPORAL_SCOPE_SUFFIX = "/secrets/db-temporal-runtime-demo"
KEY_VAULT_SECRETS_USER_ROLE = "Key Vault Secrets User"
OPTIONAL_ROLE_ASSIGNMENT_FIELDS = frozenset(
    {
        "condition",
        "delegated_managed_identity_resource_id",
        "description",
    }
)
DATABASE_BOOTSTRAP_ADMIN_ADDRESS = (
    "module.foundation.azurerm_postgresql_flexible_server_active_directory_administrator.bootstrap[0]"
)
DATABASE_PROVISIONER_ROLE_ADDRESS = "module.foundation.azurerm_role_assignment.database_provisioner_vault[0]"


def destructive_changes(plan: dict[str, Any]) -> list[str]:
    """Return resource addresses whose planned actions include deletion."""
    resource_changes = plan.get("resource_changes")
    if not isinstance(resource_changes, list):
        raise ValueError("Terraform plan must contain a resource_changes list")

    destructive: list[str] = []
    for resource_change in resource_changes:
        if not isinstance(resource_change, dict):
            raise ValueError("Terraform resource change must be an object")
        address = resource_change.get("address")
        change = resource_change.get("change")
        actions = change.get("actions") if isinstance(change, dict) else None
        if not isinstance(address, str) or not address:
            raise ValueError("Terraform resource change must have an address")
        if not isinstance(actions, list) or not actions or not all(isinstance(action, str) for action in actions):
            raise ValueError(f"Terraform resource change {address} has invalid actions")
        unknown_actions = set(actions) - KNOWN_ACTIONS
        if unknown_actions:
            raise ValueError(f"Terraform resource change {address} has unknown actions: {', '.join(sorted(unknown_actions))}")
        if "delete" in actions:
            destructive.append(address)
    return destructive


def enforce_plan(plan: dict[str, Any], scope: str, transition: str = "standard") -> None:
    """Reject deletion and replacement in an application plan."""
    destructive = destructive_changes(plan)
    if scope == "workload" and destructive:
        cutover_violations = temporal_secret_role_cutover_violations(plan)
        destructive = [address for address in destructive if not (address == TEMPORAL_ROLE_ADDRESS and not cutover_violations)]
    if scope == "foundation" and transition in {"wc124-plan-b", "wc124-schema-reconciliation"} and destructive:
        destructive = [
            address
            for address in destructive
            if not (
                address in {DATABASE_BOOTSTRAP_ADMIN_ADDRESS, DATABASE_PROVISIONER_ROLE_ADDRESS}
                and is_wc124_plan_b_revocation(plan, address)
            )
        ]
    if destructive:
        detail = ""
        if scope == "workload" and TEMPORAL_ROLE_ADDRESS in destructive:
            detail = "; Temporal cutover rejected: " + ", ".join(temporal_secret_role_cutover_violations(plan))
        raise ValueError(f"{scope.capitalize()} plan contains delete or replacement actions: " + ", ".join(destructive) + detail)
    if scope == "workload":
        enforce_temporal_contract(plan)


def is_wc124_plan_b_revocation(plan: dict[str, Any], address: str) -> bool:
    """Allow only removal of the two temporary WC-124 bootstrap authorities."""
    matches = [change for change in plan["resource_changes"] if change.get("address") == address]
    if len(matches) != 1:
        return False
    resource_change = matches[0]
    change = resource_change.get("change")
    if (
        resource_change.get("mode") != "managed"
        or not isinstance(change, dict)
        or change.get("actions") != ["delete"]
        or change.get("after") is not None
        or not isinstance(change.get("before"), dict)
    ):
        return False
    before = change["before"]
    if address == DATABASE_BOOTSTRAP_ADMIN_ADDRESS:
        return (
            resource_change.get("type") == "azurerm_postgresql_flexible_server_active_directory_administrator"
            and before.get("principal_type") == "ServicePrincipal"
            and isinstance(before.get("principal_name"), str)
            and before["principal_name"].startswith("id-waooaw-")
            and before["principal_name"].endswith("-db-bootstrap")
        )
    return (
        resource_change.get("type") == "azurerm_role_assignment"
        and before.get("role_definition_name") == "Key Vault Secrets Officer"
        and isinstance(before.get("principal_id"), str)
        and bool(before["principal_id"])
        and isinstance(before.get("scope"), str)
        and "/providers/Microsoft.KeyVault/vaults/kv-waooaw-" in before["scope"]
        and "/secrets/" not in before["scope"]
    )


def is_temporal_secret_role_cutover(plan: dict[str, Any]) -> bool:
    """Accept only the one-time Demo Temporal role scope migration."""
    return not temporal_secret_role_cutover_violations(plan)


def stable_role_field_changed(
    field: str,
    before: dict[str, Any],
    after: dict[str, Any],
    after_unknown: dict[str, Any],
) -> bool:
    """Compare stable role fields across AzureRM blank/null normalization."""
    after_value = after.get(field)
    if after_value is None and after_unknown.get(field) is True:
        return False
    before_value = before.get(field)
    if field in OPTIONAL_ROLE_ASSIGNMENT_FIELDS:
        before_value = None if before_value in ("", None) else before_value
        after_value = None if after_value in ("", None) else after_value
    return before_value != after_value


def temporal_secret_role_cutover_violations(plan: dict[str, Any]) -> list[str]:
    """Return closed-world reasons a Temporal role replacement is unsafe."""
    matches = [change for change in plan["resource_changes"] if change.get("address") == TEMPORAL_ROLE_ADDRESS]
    if len(matches) != 1:
        return [f"expected one exact resource change, found {len(matches)}"]
    resource_change = matches[0]
    if resource_change.get("mode") != "managed" or resource_change.get("type") != "azurerm_role_assignment":
        return ["resource must be a managed azurerm_role_assignment"]
    change = resource_change.get("change")
    if not isinstance(change, dict) or change.get("actions") != ["delete", "create"]:
        return ["actions must be exactly delete then create"]
    if change.get("replace_paths") != [["scope"]]:
        return [f"replacement paths must be scope only, got {change.get('replace_paths')!r}"]
    before = change.get("before")
    after = change.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        return ["before and after values must be objects"]
    before_scope = before.get("scope")
    after_scope = after.get("scope")
    if not isinstance(before_scope, str) or not isinstance(after_scope, str):
        return ["before and after scopes must be known strings"]
    if not before_scope.endswith(LEGACY_TEMPORAL_SCOPE_SUFFIX):
        return ["before scope is not the exact legacy Temporal secret"]
    if not after_scope.endswith(DATABASE_TEMPORAL_SCOPE_SUFFIX):
        return ["after scope is not the exact database Temporal secret"]
    if before_scope[: -len(LEGACY_TEMPORAL_SCOPE_SUFFIX)] != after_scope[: -len(DATABASE_TEMPORAL_SCOPE_SUFFIX)]:
        return ["before and after scopes are not in the same Key Vault"]
    if not isinstance(before.get("principal_id"), str) or not before["principal_id"]:
        return ["existing principal_id must be known and non-empty"]
    if before.get("role_definition_name") != KEY_VAULT_SECRETS_USER_ROLE:
        return ["existing role must be Key Vault Secrets User"]
    after_unknown = change.get("after_unknown")
    if after_unknown is None:
        after_unknown = {}
    if not isinstance(after_unknown, dict):
        return ["after_unknown must be an object"]
    stable_fields = (
        "condition",
        "condition_version",
        "delegated_managed_identity_resource_id",
        "description",
        "principal_id",
        "role_definition_name",
    )
    changed_fields = [field for field in stable_fields if stable_role_field_changed(field, before, after, after_unknown)]
    if changed_fields:
        return ["stable fields changed: " + ", ".join(changed_fields)]
    return []


def enforce_temporal_contract(plan: dict[str, Any]) -> None:
    """Require the Demo Temporal plan to preserve its non-destructive lifecycle contract."""
    changes = plan["resource_changes"]
    temporal_changes = [change for change in changes if change.get("address") == TEMPORAL_ADDRESS]
    if not temporal_changes:
        return
    after = temporal_changes[0].get("change", {}).get("after")
    try:
        template = after["template"][0]
        containers = {container["name"]: container for container in template["container"]}
        temporal = containers["temporal"]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("Workload plan has an incomplete Demo Temporal contract") from error
    violations: list[str] = []
    if set(containers) != {"temporal"}:
        violations.append("Temporal must use external PostgreSQL without a database sidecar")
    if template.get("min_replicas") not in {0, 1} or template.get("max_replicas") != 1:
        violations.append("Temporal must be dormant or run as one fixed replica")
    # Container Apps probes connect over loopback; the image binds to the replica IP by
    # default, so probes are only valid when the server binds on every interface.
    env = {entry.get("name"): entry.get("value") for entry in temporal.get("env") or []}
    if env.get("BIND_ON_IP") != "0.0.0.0":  # noqa: S104
        violations.append("Temporal must bind on 0.0.0.0 so Container Apps probes reach the frontend")
    args = " ".join(str(arg) for arg in temporal.get("args") or [])
    if "TEMPORAL_BROADCAST_ADDRESS=" not in args:
        violations.append("Temporal must advertise its routable replica address through TEMPORAL_BROADCAST_ADDRESS")
    # azurerm 4.14 rejects failure_count_threshold above 30 at plan time (runs 39446836598 and
    # 39454383100); the policy bound must never exceed what the provider can apply.
    for probe_kind, bound in (("startup_probe", 30), ("readiness_probe", 10)):
        probes = temporal.get(probe_kind) or []
        if len(probes) != 1:
            violations.append(f"Temporal {probe_kind.replace('_', ' ')} must be defined exactly once")
            continue
        probe = probes[0]
        if probe.get("transport") != "TCP" or probe.get("port") != 7233:
            violations.append(f"Temporal {probe_kind.replace('_', ' ')} must be TCP on 7233")
        threshold = probe.get("failure_count_threshold")
        if not isinstance(threshold, int) or not 1 <= threshold <= bound:
            violations.append(f"Temporal {probe_kind.replace('_', ' ')} failure threshold must be within 1..{bound}")
    if "@sha256:" not in str(temporal.get("image", "")):
        violations.append("Temporal image must be digest-pinned")
    if violations:
        raise ValueError("Workload plan violates Demo Temporal contract: " + "; ".join(violations))


def enforce_foundation_plan(plan: dict[str, Any]) -> None:
    """Preserve the foundation-specific policy API for existing callers."""
    enforce_plan(plan, "foundation")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--scope", required=True, choices=("foundation", "workload"))
    parser.add_argument(
        "--transition",
        default="standard",
        choices=("standard", "wc124-plan-b", "wc124-schema-reconciliation"),
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        plan = json.loads(arguments.plan.read_text(encoding="utf-8"))
        if not isinstance(plan, dict):
            raise ValueError("Terraform plan JSON must be an object")
        if arguments.transition != "standard" and arguments.scope != "foundation":
            raise ValueError("WC-124 database transitions are valid only for foundation plans")
        enforce_plan(plan, arguments.scope, arguments.transition)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    result = {
        "schema": "waooaw.terraform-plan-policy-result/v1",
        "status": "PASS",
        "scope": arguments.scope,
        "transition": arguments.transition,
        "plan_json_sha256": "sha256:" + hashlib.sha256(arguments.plan.read_bytes()).hexdigest(),
        "destructive_changes": 0,
    }
    if arguments.output is not None:
        arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

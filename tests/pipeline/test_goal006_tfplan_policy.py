from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from goal006_tfplan_policy import enforce_plan


ROOT = Path(__file__).resolve().parents[2]


def destructive_plan() -> dict[str, object]:
    return {
        "resource_changes": [
            {
                "address": 'module.workload.azurerm_container_app.member["web"]',
                "change": {"actions": ["delete"]},
            }
        ]
    }


def test_policy_cli_writes_plan_bound_pass_evidence(tmp_path: Path) -> None:
    plan = tmp_path / "plan.json"
    result = tmp_path / "policy.json"
    plan.write_text(json.dumps({"resource_changes": []}), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/goal006_tfplan_policy.py"),
            "--scope",
            "foundation",
            "--plan",
            str(plan),
            "--output",
            str(result),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(result.read_text(encoding="utf-8")) == json.loads(completed.stdout)


def temporal_plan(
    *,
    startup_probe: list[object] | None = None,
    readiness_probe: list[object] | None = None,
    min_replicas: int = 1,
    include_postgres_sidecar: bool = False,
    bind_on_ip: str | None = "0.0.0.0",
    args: list[str] | None = None,
) -> dict[str, object]:
    if startup_probe is None:
        startup_probe = [{"transport": "TCP", "port": 7233, "failure_count_threshold": 30}]
    if readiness_probe is None:
        readiness_probe = [{"transport": "TCP", "port": 7233, "failure_count_threshold": 3}]
    if args is None:
        args = ['export TEMPORAL_BROADCAST_ADDRESS="$(hostname -i)"\nexec /etc/temporal/entrypoint.sh autosetup\n']
    containers = [
        {
            "name": "temporal",
            "image": f"temporalio/auto-setup@sha256:{'a' * 64}",
            "env": [] if bind_on_ip is None else [{"name": "BIND_ON_IP", "value": bind_on_ip}],
            "args": args,
            "startup_probe": startup_probe,
            "readiness_probe": readiness_probe,
        }
    ]
    if include_postgres_sidecar:
        containers.append(
            {
                "name": "postgres",
                "image": f"postgres@sha256:{'b' * 64}",
            }
        )
    return {
        "resource_changes": [
            {
                "address": "module.workload.azurerm_container_app.temporal[0]",
                "change": {
                    "actions": ["update"],
                    "after": {
                        "template": [
                            {
                                "min_replicas": min_replicas,
                                "max_replicas": 1,
                                "container": containers,
                            }
                        ]
                    },
                },
            }
        ]
    }


def temporal_secret_role_cutover() -> dict[str, Any]:
    vault = "/subscriptions/sub/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo"
    stable = {
        "condition": None,
        "condition_version": None,
        "delegated_managed_identity_resource_id": None,
        "description": None,
        "principal_id": "cb3198d4-856a-4631-a667-385aa46136e5",
        "role_definition_name": "Key Vault Secrets User",
    }
    return {
        "resource_changes": [
            {
                "address": "module.workload.azurerm_role_assignment.temporal_secret[0]",
                "mode": "managed",
                "type": "azurerm_role_assignment",
                "name": "temporal_secret",
                "index": 0,
                "change": {
                    "actions": ["delete", "create"],
                    "before": {
                        **stable,
                        "scope": f"{vault}/secrets/business-platform",
                    },
                    "after": {
                        **stable,
                        "scope": f"{vault}/secrets/db-temporal-runtime-demo",
                    },
                    "after_unknown": {},
                    "replace_paths": [["scope"]],
                },
            }
        ]
    }


@pytest.mark.parametrize("scope", ["foundation", "workload"])
def test_destructive_plan_error_names_its_scope(scope: str) -> None:
    with pytest.raises(ValueError, match=f"^{scope.capitalize()} plan contains"):
        enforce_plan(destructive_plan(), scope)


def test_workload_plan_accepts_safe_temporal_contract() -> None:
    enforce_plan(temporal_plan(), "workload")


def test_workload_plan_accepts_dormant_temporal_contract() -> None:
    enforce_plan(temporal_plan(min_replicas=0), "workload")


def test_workload_plan_rejects_temporal_postgres_sidecar() -> None:
    with pytest.raises(ValueError, match="without a database sidecar"):
        enforce_plan(temporal_plan(include_postgres_sidecar=True), "workload")


def test_workload_plan_rejects_temporal_replica_drift() -> None:
    with pytest.raises(ValueError, match="dormant or run as one fixed replica"):
        enforce_plan(temporal_plan(min_replicas=2), "workload")


def test_workload_plan_rejects_unbounded_temporal_startup_probe() -> None:
    with pytest.raises(ValueError, match=r"startup probe failure threshold must be within 1\.\.30"):
        enforce_plan(
            temporal_plan(startup_probe=[{"transport": "TCP", "port": 7233, "failure_count_threshold": 240}]),
            "workload",
        )


def test_workload_plan_rejects_temporal_startup_probe_above_provider_limit() -> None:
    # 36 passed the old 1..60 policy but azurerm 4.14 refused it in the Demo workload plan.
    with pytest.raises(ValueError, match=r"startup probe failure threshold must be within 1\.\.30"):
        enforce_plan(
            temporal_plan(startup_probe=[{"transport": "TCP", "port": 7233, "failure_count_threshold": 36}]),
            "workload",
        )


def test_workload_plan_rejects_missing_temporal_probes() -> None:
    with pytest.raises(ValueError, match="startup probe must be defined exactly once"):
        enforce_plan(temporal_plan(startup_probe=[]), "workload")
    with pytest.raises(ValueError, match="readiness probe must be defined exactly once"):
        enforce_plan(temporal_plan(readiness_probe=[]), "workload")


def test_workload_plan_rejects_temporal_http_probe() -> None:
    with pytest.raises(ValueError, match="readiness probe must be TCP on 7233"):
        enforce_plan(
            temporal_plan(readiness_probe=[{"transport": "HTTP", "port": 7233, "failure_count_threshold": 3}]),
            "workload",
        )


def test_workload_plan_rejects_temporal_replica_ip_bind() -> None:
    with pytest.raises(ValueError, match="must bind on 0.0.0.0"):
        enforce_plan(temporal_plan(bind_on_ip=None), "workload")


def test_workload_plan_rejects_temporal_without_broadcast_address() -> None:
    with pytest.raises(ValueError, match="TEMPORAL_BROADCAST_ADDRESS"):
        enforce_plan(temporal_plan(args=["exec /etc/temporal/entrypoint.sh autosetup"]), "workload")


def test_workload_plan_accepts_exact_temporal_secret_role_cutover() -> None:
    enforce_plan(temporal_secret_role_cutover(), "workload")


def test_workload_plan_accepts_provider_computed_stable_cutover_fields() -> None:
    plan = temporal_secret_role_cutover()
    change = plan["resource_changes"][0]["change"]
    for field in ("condition_version", "principal_id", "role_definition_name"):
        change["after"][field] = None
        change["after_unknown"][field] = True

    enforce_plan(plan, "workload")


def test_workload_plan_accepts_azurerm_blank_to_null_optional_fields() -> None:
    plan = temporal_secret_role_cutover()
    change = plan["resource_changes"][0]["change"]
    for field in ("condition", "condition_version", "delegated_managed_identity_resource_id", "description"):
        change["before"][field] = ""
        change["after"][field] = None
    change["after_unknown"]["condition_version"] = True

    enforce_plan(plan, "workload")


def test_workload_plan_rejects_removed_nonempty_optional_field() -> None:
    plan = temporal_secret_role_cutover()
    change = plan["resource_changes"][0]["change"]
    change["before"]["description"] = "required assignment"
    change["after"]["description"] = None

    with pytest.raises(ValueError, match=r"stable fields changed: description"):
        enforce_plan(plan, "workload")


def mutate_cutover(path: tuple[str, ...], value: object) -> dict[str, Any]:
    plan = temporal_secret_role_cutover()
    target = plan["resource_changes"][0]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return plan


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("address",), 'module.workload.azurerm_role_assignment.member_database_secret["web"]'),
        (("mode",), "data"),
        (("type",), "azurerm_key_vault_secret"),
        (("change", "actions"), ["create", "delete"]),
        (("change", "replace_paths"), [["principal_id"]]),
        (("change", "before", "scope"), "/subscriptions/sub/secrets/other"),
        (("change", "after", "scope"), "/subscriptions/sub/secrets/db-temporal-runtime-demo"),
        (("change", "after", "principal_id"), "different-principal"),
        (("change", "after", "role_definition_name"), "Key Vault Administrator"),
    ],
)
def test_workload_plan_rejects_near_match_temporal_role_replacements(
    path: tuple[str, ...],
    value: object,
) -> None:
    with pytest.raises(ValueError, match="delete or replacement"):
        enforce_plan(mutate_cutover(path, value), "workload")


def test_workload_plan_rejects_duplicate_temporal_role_replacements() -> None:
    plan = temporal_secret_role_cutover()
    plan["resource_changes"].append(plan["resource_changes"][0])

    with pytest.raises(ValueError, match="delete or replacement"):
        enforce_plan(plan, "workload")


def test_workload_plan_rejects_invalid_unknown_marker_for_changed_principal() -> None:
    plan = temporal_secret_role_cutover()
    change = plan["resource_changes"][0]["change"]
    change["after"]["principal_id"] = None
    change["after_unknown"]["principal_id"] = "yes"

    with pytest.raises(ValueError, match=r"stable fields changed: principal_id"):
        enforce_plan(plan, "workload")


def test_workload_plan_rejects_extra_destructive_change_beside_cutover() -> None:
    plan = temporal_secret_role_cutover()
    plan["resource_changes"].extend(destructive_plan()["resource_changes"])

    with pytest.raises(ValueError, match=r"delete or replacement.*container_app\.member"):
        enforce_plan(plan, "workload")


def test_foundation_plan_never_accepts_temporal_role_cutover() -> None:
    with pytest.raises(ValueError, match="Foundation plan contains"):
        enforce_plan(temporal_secret_role_cutover(), "foundation")


def wc124_plan_b() -> dict[str, Any]:
    vault = "/subscriptions/sub/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo"
    return {
        "resource_changes": [
            {
                "address": ("module.foundation.azurerm_postgresql_flexible_server_active_directory_administrator.bootstrap[0]"),
                "mode": "managed",
                "type": "azurerm_postgresql_flexible_server_active_directory_administrator",
                "change": {
                    "actions": ["delete"],
                    "before": {
                        "principal_name": "id-waooaw-demo-db-bootstrap",
                        "principal_type": "ServicePrincipal",
                    },
                    "after": None,
                },
            },
            {
                "address": "module.foundation.azurerm_role_assignment.database_provisioner_vault[0]",
                "mode": "managed",
                "type": "azurerm_role_assignment",
                "change": {
                    "actions": ["delete"],
                    "before": {
                        "principal_id": "provisioner-principal",
                        "role_definition_name": "Key Vault Secrets Officer",
                        "scope": vault,
                    },
                    "after": None,
                },
            },
        ]
    }


def test_foundation_plan_accepts_exact_wc124_plan_b_revocations() -> None:
    enforce_plan(wc124_plan_b(), "foundation", "wc124-plan-b")


def test_foundation_plan_accepts_exact_wc124_schema_reconciliation_transition() -> None:
    enforce_plan(wc124_plan_b(), "foundation", "wc124-schema-reconciliation")


def test_foundation_standard_plan_rejects_wc124_plan_b_revocations() -> None:
    with pytest.raises(ValueError, match="delete or replacement"):
        enforce_plan(wc124_plan_b(), "foundation")


@pytest.mark.parametrize(
    ("index", "field", "value"),
    [
        (0, "principal_name", "id-waooaw-demo-deployment"),
        (0, "principal_type", "User"),
        (1, "role_definition_name", "Key Vault Administrator"),
        (1, "scope", "/subscriptions/sub/resourceGroups/other"),
    ],
)
def test_foundation_plan_rejects_near_match_wc124_plan_b_revocations(
    index: int,
    field: str,
    value: str,
) -> None:
    plan = wc124_plan_b()
    plan["resource_changes"][index]["change"]["before"][field] = value

    with pytest.raises(ValueError, match="delete or replacement"):
        enforce_plan(plan, "foundation", "wc124-plan-b")

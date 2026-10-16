#!/usr/bin/env python3
"""Execute ordered WC-124 Azure activation or retained-data sleep steps."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §§10-11
# Constitutional basis: C-023, C-059, C-066, C-080

from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


APPLICATIONS = (
    "constitutional-engine",
    "business-platform",
    "professional-runtime",
    "ai-runtime",
    "web",
    "billing-engine",
    "dma",
)
DEPENDENCIES = ("keycloak", "temporal", "auth-redis")
SLEEP_GATES = {
    "ingress_closed",
    "work_drained",
    "migration_idle",
    "backup_ready",
    "rollback_ready",
    "billing_watermark_recorded",
}
POSTGRESQL_TRANSITIONAL_STATES = {"Starting", "Stopping", "Updating"}


class AzureLifecycleError(RuntimeError):
    """A provider lifecycle operation failed closed."""


def run(arguments: Sequence[str]) -> str:
    result = subprocess.run(  # noqa: S603
        arguments,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        diagnostics = "\n".join(part.strip() for part in (result.stderr, result.stdout) if part.strip())[-4000:]
        raise AzureLifecycleError(f"command failed ({result.returncode}): {arguments[0]} {arguments[1]}\n{diagnostics}")
    return result.stdout


def validate_sleep_gates(evidence: dict[str, Any]) -> None:
    if set(evidence) != SLEEP_GATES or any(evidence[field] is not True for field in SLEEP_GATES):
        raise AzureLifecycleError("sleep gates are incomplete or not all PASS")


def postgresql_state(environment: str, runner: Callable[[Sequence[str]], str]) -> str:
    state = runner(
        [
            "az",
            "postgres",
            "flexible-server",
            "show",
            "--resource-group",
            f"waooaw-{environment}-rg",
            "--name",
            f"psql-waooaw-{environment}-state",
            "--query",
            "state",
            "--output",
            "tsv",
        ]
    ).strip()
    if not state:
        raise AzureLifecycleError("PostgreSQL state query returned no state")
    return state


def commands(environment: str, action: str) -> list[list[str]]:
    if environment not in {"demo", "uat"}:
        raise AzureLifecycleError("Azure lifecycle is authorized only for Demo and UAT")
    resource_group = f"waooaw-{environment}-rg"
    server = f"psql-waooaw-{environment}-state"
    if action == "activate":
        return [
            [
                "az",
                "postgres",
                "flexible-server",
                "start",
                "--resource-group",
                resource_group,
                "--name",
                server,
                "--output",
                "none",
            ],
        ]
    if action != "sleep":
        raise AzureLifecycleError("action must be activate or sleep")
    result: list[list[str]] = []
    for member in ("web", "business-platform", "professional-runtime"):
        result.append(
            [
                "az",
                "containerapp",
                "ingress",
                "disable",
                "--resource-group",
                resource_group,
                "--name",
                f"ca-{environment}-{member}",
                "--output",
                "none",
            ]
        )
    for member in (*APPLICATIONS, *DEPENDENCIES, "pgbouncer"):
        if environment == "uat" and member == "temporal":
            continue
        result.append(
            [
                "az",
                "containerapp",
                "update",
                "--resource-group",
                resource_group,
                "--name",
                f"ca-{environment}-{member}",
                "--min-replicas",
                "0",
                "--max-replicas",
                "1",
                "--output",
                "none",
            ]
        )
    result.append(
        [
            "az",
            "postgres",
            "flexible-server",
            "stop",
            "--resource-group",
            resource_group,
            "--name",
            server,
            "--output",
            "none",
        ]
    )
    return result


def execute(
    environment: str,
    action: str,
    *,
    sleep_evidence: dict[str, Any] | None,
    runner: Callable[[Sequence[str]], str] = run,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if action == "sleep":
        if sleep_evidence is None:
            raise AzureLifecycleError("sleep evidence is required")
        validate_sleep_gates(sleep_evidence)
    planned = commands(environment, action)
    initial_postgresql_state = postgresql_state(environment, runner)
    if initial_postgresql_state not in {"Ready", "Stopped"}:
        raise AzureLifecycleError(f"PostgreSQL lifecycle denied from state {initial_postgresql_state}; expected Ready or Stopped")
    completed: list[str] = []
    for command in planned:
        postgres_operation = tuple(command[1:4])
        if postgres_operation in {
            ("postgres", "flexible-server", "start"),
            ("postgres", "flexible-server", "stop"),
        }:
            current_state = initial_postgresql_state if action == "activate" else postgresql_state(environment, runner)
            target_state = "Ready" if command[3] == "start" else "Stopped"
            required_state = "Stopped" if command[3] == "start" else "Ready"
            if current_state == target_state:
                completed.append(f"postgres flexible-server already-{target_state.lower()}")
                continue
            if current_state != required_state:
                raise AzureLifecycleError(
                    f"PostgreSQL {command[3]} denied from state {current_state}; expected {required_state} or {target_state}"
                )
        runner(command)
        completed.append(f"{command[1]} {command[2]}")
        if postgres_operation == ("postgres", "flexible-server", "start"):
            for _ in range(60):
                state = postgresql_state(environment, runner)
                if state == "Ready":
                    break
                if state not in POSTGRESQL_TRANSITIONAL_STATES:
                    raise AzureLifecycleError(f"PostgreSQL entered unexpected state {state} while starting")
                sleeper(5)
            else:
                raise AzureLifecycleError("PostgreSQL did not become Ready")
        if postgres_operation == ("postgres", "flexible-server", "stop"):
            for _ in range(60):
                state = postgresql_state(environment, runner)
                if state == "Stopped":
                    break
                if state not in POSTGRESQL_TRANSITIONAL_STATES:
                    raise AzureLifecycleError(f"PostgreSQL entered unexpected state {state} while stopping")
                sleeper(5)
            else:
                raise AzureLifecycleError("PostgreSQL did not stop")
        if action == "sleep" and command[1:3] == ["containerapp", "update"]:
            app_name = command[command.index("--name") + 1]
            for _ in range(60):
                revisions = json.loads(
                    runner(
                        [
                            "az",
                            "containerapp",
                            "revision",
                            "list",
                            "--resource-group",
                            f"waooaw-{environment}-rg",
                            "--name",
                            app_name,
                            "--query",
                            "[?properties.active].name",
                            "--output",
                            "json",
                        ]
                    )
                )
                replica_count = 0
                for revision in revisions:
                    replica_count += int(
                        runner(
                            [
                                "az",
                                "containerapp",
                                "replica",
                                "list",
                                "--resource-group",
                                f"waooaw-{environment}-rg",
                                "--name",
                                app_name,
                                "--revision",
                                revision,
                                "--query",
                                "length(@)",
                                "--output",
                                "tsv",
                            ]
                        ).strip()
                    )
                if replica_count == 0:
                    break
                sleeper(5)
            else:
                raise AzureLifecycleError(f"{app_name} did not scale to zero")
    return {
        "schema": "waooaw.wc124-azure-lifecycle-execution/v1",
        "environment": environment,
        "action": action,
        "completed_steps": completed,
        "retained_authoritative_data": True,
        "residual_monthly_cost": (
            {"currency": "INR", "estimate": 1100 if environment == "demo" else 1600} if action == "sleep" else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("demo", "uat"), required=True)
    parser.add_argument("--action", choices=("activate", "sleep"), required=True)
    parser.add_argument("--sleep-evidence", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    evidence = json.loads(arguments.sleep_evidence.read_text(encoding="utf-8")) if arguments.sleep_evidence else None
    record = execute(
        arguments.environment,
        arguments.action,
        sleep_evidence=evidence,
    )
    arguments.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

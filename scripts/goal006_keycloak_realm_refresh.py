#!/usr/bin/env python3
"""Restart Keycloak replicas that predate the realm import of this deployment.

Every Demo apply drops and recreates ``waooaw_keycloak`` and the migration job re-imports the
realm with ``kc.sh import --override true``. A Keycloak replica that was already running keeps
its cached realm and client models, whose IDs no longer exist, so every authorization request
fails with "Client not found" while the revision still reports Healthy (run 41014026210). This
gate compares each replica's creation time with the import's end time, restarts the latest ready
revision when any replica is older, and waits until every replica is newer and ready.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "waooaw.goal006-keycloak-realm-refresh/v1"


def parse_time(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} has no timezone: {value}")
    return parsed


def import_completed_at(execution: dict[str, Any]) -> datetime:
    properties = execution.get("properties") or {}
    if properties.get("status") != "Succeeded":
        raise ValueError(f"Keycloak realm import did not succeed: status={properties.get('status')}")
    return parse_time(properties.get("endTime"), "Keycloak realm import endTime")


def stale_replicas(replicas: list[dict[str, Any]], imported_at: datetime) -> list[str]:
    return [
        str(replica.get("name"))
        for replica in replicas
        if parse_time((replica.get("properties") or {}).get("createdTime"), f"{replica.get('name')} createdTime") <= imported_at
    ]


def replicas_ready(replicas: list[dict[str, Any]]) -> bool:
    return bool(replicas) and all(
        (replica.get("properties") or {}).get("runningState") == "Running"
        and all(container.get("ready") is True for container in (replica.get("properties") or {}).get("containers") or [])
        for replica in replicas
    )


def refresh(
    resource_group: str,
    environment: str,
    execution: dict[str, Any],
    run_az: Callable[[list[str]], Any],
    timeout_seconds: int,
    interval_seconds: int,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if environment not in {"demo", "uat"} or resource_group != f"waooaw-{environment}-rg":
        raise ValueError("Keycloak realm refresh is restricted to the same-environment Demo/UAT resource group")
    app = f"ca-{environment}-keycloak"
    imported_at = import_completed_at(execution)
    revision = run_az(
        [
            "containerapp",
            "show",
            "--resource-group",
            resource_group,
            "--name",
            app,
            "--query",
            "properties.latestReadyRevisionName",
        ]
    )
    if not isinstance(revision, str) or not revision.startswith(f"{app}--"):
        raise ValueError(f"{app}: unexpected latest ready revision {revision!r}")

    def list_replicas() -> list[dict[str, Any]]:
        replicas = run_az(
            ["containerapp", "replica", "list", "--resource-group", resource_group, "--name", app, "--revision", revision]
        )
        if not isinstance(replicas, list):
            raise ValueError(f"{app}: replica list is not a list")
        return replicas

    replicas = list_replicas()
    stale = stale_replicas(replicas, imported_at)
    evidence: dict[str, Any] = {
        "schema": SCHEMA,
        "environment": environment,
        "app": app,
        "revision": revision,
        "import_completed_at": imported_at.isoformat(),
        "stale_replicas": stale,
        "restarted": False,
    }
    if replicas and not stale:
        print(f"{app}: every replica of {revision} started after the realm import; no restart needed", flush=True)
        evidence["ready"] = replicas_ready(replicas)
        if not evidence["ready"]:
            raise RuntimeError(f"{app}: replicas of {revision} are not ready")
        return evidence

    print(f"{app}: restarting {revision}; replicas older than the realm import: {stale or 'none listed'}", flush=True)
    run_az(["containerapp", "revision", "restart", "--resource-group", resource_group, "--name", app, "--revision", revision])
    evidence["restarted"] = True
    deadline = monotonic() + timeout_seconds
    while True:
        replicas = list_replicas()
        stale = stale_replicas(replicas, imported_at)
        ready = replicas_ready(replicas)
        print(f"{app}: replicas={len(replicas)} stale={len(stale)} ready={ready}", flush=True)
        if replicas and not stale and ready:
            evidence["ready"] = True
            evidence["replicas"] = [replica.get("name") for replica in replicas]
            return evidence
        if monotonic() >= deadline:
            raise RuntimeError(f"{app}: replicas did not refresh after the realm import within {timeout_seconds}s")
        sleep(interval_seconds)


def _run_az(args: list[str]) -> Any:
    completed = subprocess.run(  # noqa: S603
        ["az", *args, "--output", "json"],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"az {' '.join(args[:3])} failed ({completed.returncode}): {completed.stderr.strip()}")
    return json.loads(completed.stdout or "null")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--environment", required=True, choices=("demo", "uat"))
    parser.add_argument("--migration-execution", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=420)
    parser.add_argument("--interval-seconds", type=int, default=10)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args(argv)
    try:
        evidence = refresh(
            arguments.resource_group,
            arguments.environment,
            json.loads(arguments.migration_execution.read_text(encoding="utf-8")),
            _run_az,
            arguments.timeout_seconds,
            arguments.interval_seconds,
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Keycloak realm refresh failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    arguments.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

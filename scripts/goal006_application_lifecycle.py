#!/usr/bin/env python3
"""Start/stop existing Demo Container Apps without deploying or touching databases."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any
from collections.abc import Callable

from goal006_activation_readiness import _run_az, observe_revision

SUBSCRIPTION = "2ed11839-6a0f-4eaa-bd94-44ca96ff5d84"
API_VERSION = "2025-01-01"
START_ORDER = (
    "pgbouncer",
    "auth-redis",
    "keycloak",
    "identity-edge",
    "temporal",
    "constitutional-engine",
    "business-platform",
    "billing-engine",
    "ai-runtime",
    "professional-runtime",
    "dma",
    "web",
)


def fingerprint(app: dict[str, Any], revisions: list[dict[str, Any]]) -> str:
    properties = app["properties"]
    retained = {
        "template": properties["template"],
        "configuration": properties["configuration"],
        "revisions": sorted((r["name"], r["properties"]["active"]) for r in revisions),
    }
    return hashlib.sha256(json.dumps(retained, sort_keys=True).encode()).hexdigest()


def execute(
    environment: str,
    action: str,
    *,
    run_az: Callable[[list[str]], Any] = _run_az,
    timeout: int = 600,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if environment != "demo" or action not in {"Start", "Stop"}:
        raise ValueError("Only Demo Start/Stop is enabled; UAT is excluded by Founder decision")
    operation_deadline = clock() + 1800
    result = evidence if evidence is not None else {}
    result.update(schema="waooaw.application-lifecycle/v1", environment=environment, action=action, status="failed", apps=[])
    group = f"waooaw-{environment}-rg"
    members = list(START_ORDER)
    expected = {f"ca-{environment}-{member}" for member in members}
    inventory = run_az(["containerapp", "list", "--resource-group", group])
    found = {app["name"] for app in inventory}
    if found != expected:
        raise ValueError(f"App inventory mismatch: missing={sorted(expected - found)} unexpected={sorted(found - expected)}")
    snapshots = {}
    for app in inventory:
        name = app["name"]
        containers = app["properties"]["template"].get("containers", [])
        if any("postgres" in (container["name"] + " " + container.get("image", "")).lower() for container in containers):
            raise ValueError(f"{name}: embedded PostgreSQL would violate database exclusion")
        revisions = run_az(["containerapp", "revision", "list", "-g", group, "-n", name, "--all"])
        if app["properties"].get("runningStatus") not in {"Running", "Stopped"}:
            raise ValueError(f"{name}: application is not in a settled Running/Stopped state")
        snapshots[name] = fingerprint(app, revisions)
    if action == "Stop":
        members.reverse()
    for member in members:
        name = f"ca-{environment}-{member}"
        args = ["-g", group, "-n", name]
        app = run_az(["containerapp", "show", *args])
        revisions = run_az(["containerapp", "revision", "list", *args, "--all"])
        if fingerprint(app, revisions) != snapshots[name]:
            raise ValueError(f"{name}: deployment/configuration changed during lifecycle operation")
        target = "Running" if action == "Start" else "Stopped"
        entry = {"app": name, "target": target, "status": "pending", "configuration_digest": snapshots[name]}
        result["apps"].append(entry)
        if app["properties"]["runningStatus"] != target:
            resource = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/{group}/providers/Microsoft.App/containerApps/{name}"
            run_az(
                [
                    "rest",
                    "--method",
                    "post",
                    "--url",
                    f"https://management.azure.com{resource}/{action.lower()}?api-version={API_VERSION}",
                ]
            )
        deadline = min(clock() + timeout, operation_deadline)
        while True:
            observed = run_az(["containerapp", "show", *args])
            revisions = run_az(["containerapp", "revision", "list", *args, "--all"])
            if fingerprint(observed, revisions) != snapshots[name]:
                raise ValueError(f"{name}: lifecycle operation changed revision/configuration identity")
            properties = observed["properties"]
            if properties.get("provisioningState") == "Failed":
                raise RuntimeError(f"{name}: Azure provisioning failed")
            settled = properties.get("runningStatus") == target
            if action == "Stop":
                settled = settled and all(r["properties"].get("replicas") == 0 for r in revisions)
            elif settled:
                settled = observe_revision(group, name, run_az)["ready"]
            if settled:
                entry["status"] = "passed"
                break
            if clock() >= deadline:
                raise RuntimeError(f"{name}: timed out waiting for {target} and revision verification")
            sleep(5)
    result["status"] = "passed"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("demo",), required=True)
    parser.add_argument("--action", choices=("Start", "Stop"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, Any] = {}
    try:
        execute(args.environment, args.action, evidence=result)
    except (ValueError, KeyError, TypeError, RuntimeError) as error:
        result.update(status="failed", error=str(error))
        print(f"::error::Application lifecycle failed: {error}", file=sys.stderr)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

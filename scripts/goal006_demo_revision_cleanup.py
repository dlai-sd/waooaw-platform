#!/usr/bin/env python3
"""Retire zero-traffic Demo revisions only after the latest revision is healthy."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from goal006_activation_readiness import _run_az, list_container_apps


def plan_app(resource_group: str, app: str, run_az: Callable[[list[str]], Any]) -> dict[str, Any]:
    args = ["--resource-group", resource_group, "--name", app]
    shown = run_az(["containerapp", "show", *args])
    properties = shown["properties"]
    latest = properties.get("latestRevisionName")
    revisions = run_az(["containerapp", "revision", "list", *args, "--all"])
    active = [revision for revision in revisions if revision["properties"]["active"]]
    candidates = [revision["name"] for revision in active if revision["name"] != latest]
    plan = {"app": app, "latest": latest, "obsolete": sorted(candidates)}
    if not candidates:
        if len(active) != 1 or not latest or active[0]["name"] != latest:
            raise ValueError(f"{app}: expected one active latest revision")
        return plan
    if latest != properties.get("latestReadyRevisionName"):
        raise ValueError(f"{app}: latest revision is not the latest ready revision")
    current = next((revision for revision in active if revision["name"] == latest), None)
    if not current or current["properties"].get("healthState") != "Healthy":
        raise ValueError(f"{app}: latest revision is not active and healthy")
    ingress = properties["configuration"].get("ingress") or {}
    traffic = ingress.get("traffic") or []
    # Refuse split traffic and revision labels, including zero-weight labelled routes.
    if (
        sum(route.get("weight", 0) for route in traffic) != 100
        or any(route.get("label") for route in traffic)
        or any(
            route.get("weight", 0) > 0 and not (route.get("latestRevision") is True or route.get("revisionName") == latest)
            for route in traffic
        )
        or any(revision["properties"].get("trafficWeight", 0) > 0 for revision in active if revision["name"] in candidates)
    ):
        raise ValueError(f"{app}: obsolete revision may still have traffic or a labelled route")
    return plan


def reconcile(
    resource_group: str,
    *,
    apply: bool,
    run_az: Callable[[list[str]], Any] = _run_az,
    timeout_seconds: int = 120,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if resource_group != "waooaw-demo-rg":
        raise ValueError("Revision cleanup is authorized only for waooaw-demo-rg")
    apps = list_container_apps(resource_group, "demo", run_az)
    if not apps:
        raise ValueError("No Demo apps found; refusing an empty cleanup result")
    # Validate the entire inventory before performing any mutation.
    plans = [plan_app(resource_group, app, run_az) for app in apps]
    retired = []
    if apply:
        for plan in plans:
            for revision in plan["obsolete"]:
                current = plan_app(resource_group, plan["app"], run_az)
                if current["latest"] != plan["latest"] or revision not in current["obsolete"]:
                    raise ValueError(f"{plan['app']}: rollout changed during cleanup; retry after it settles")
                args = ["--resource-group", resource_group, "--name", plan["app"], "--revision", revision]
                run_az(["containerapp", "revision", "deactivate", *args])
                deadline = clock() + timeout_seconds
                while True:
                    observed = run_az(["containerapp", "revision", "show", *args])["properties"]
                    if observed.get("active") is False and observed.get("replicas") == 0:
                        break
                    if clock() >= deadline:
                        raise RuntimeError(f"{revision}: deactivation did not reach zero replicas")
                    sleep(5)
                retired.append({"app": plan["app"], "revision": revision})
        final = [plan_app(resource_group, app, run_az) for app in apps]
        if any(plan["obsolete"] for plan in final):
            raise ValueError("Obsolete active revisions remain after cleanup")
    return {
        "schema": "waooaw.goal006-demo-revision-cleanup/v1",
        "resource_group": resource_group,
        "mode": "apply" if apply else "plan",
        "plans": plans,
        "retired": retired,
        "status": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = reconcile(args.resource_group, apply=args.apply)
    except (ValueError, KeyError, TypeError, RuntimeError) as error:
        result = {"schema": "waooaw.goal006-demo-revision-cleanup/v1", "status": "failed", "error": str(error)}
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"::error::Demo revision cleanup failed: {error}", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

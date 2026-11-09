#!/usr/bin/env python3
"""Exclude old Demo dispatch replicas before activating a recovery-aware candidate."""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from goal006_activation_readiness import _run_az

MEMBERS = ("business-platform", "professional-runtime", "ai-runtime", "constitutional-engine")


def _revision_is_live(properties: dict[str, Any]) -> bool:
    active = properties.get("active")
    replicas = properties.get("replicas")
    if type(active) is not bool or type(replicas) is not int or replicas < 0:
        raise ValueError("Revision inventory must provide active state and a nonnegative replica count")
    return active or replicas != 0


def _old_dispatch_revisions(revisions: Any, image: str) -> list[str]:
    if not isinstance(revisions, list):
        raise ValueError("Invalid revision inventory")
    old = []
    for revision in revisions:
        if not isinstance(revision, dict) or not isinstance(revision.get("name"), str) or not revision["name"]:
            raise ValueError("Invalid revision identity")
        properties = revision.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("Invalid revision properties")
        live = _revision_is_live(properties)
        template = properties.get("template")
        containers = template.get("containers") if isinstance(template, dict) else None
        # The workload module defines one application container per dispatch member.
        if (
            not isinstance(containers, list)
            or len(containers) != 1
            or not isinstance(containers[0], dict)
            or not isinstance(containers[0].get("image"), str)
            or not containers[0]["image"]
        ):
            raise ValueError("Dispatch revision must identify exactly one application container image")
        if live and containers[0]["image"] != image:
            old.append(revision["name"])
    return old


def quiesce(
    resource_group: str,
    images: dict[str, str],
    *,
    run_az: Callable[[list[str]], Any] = _run_az,
    timeout_seconds: int = 180,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if resource_group != "waooaw-demo-rg":
        raise ValueError("Dispatch rollout exclusion is restricted to the Demo resource group")
    for member in MEMBERS:
        if not re.fullmatch(r".+@sha256:[0-9a-f]{64}", images.get(member, "")):
            raise ValueError("Dispatch rollout requires exact candidate image digests")
    apps = run_az(["containerapp", "list", "--resource-group", resource_group, "--query", "[].name"])
    if not isinstance(apps, list) or not all(isinstance(app, str) for app in apps):
        raise ValueError("Invalid application inventory")
    plans: list[tuple[str, str]] = []
    for member in MEMBERS:
        app = f"ca-demo-{member}"
        if app not in apps:
            continue
        args = ["--resource-group", resource_group, "--name", app]
        revisions = run_az(["containerapp", "revision", "list", *args, "--all"])
        plans.extend((app, name) for name in _old_dispatch_revisions(revisions, images[member]))
    # Validate the complete inventory before mutation.
    for app, revision in plans:
        args = ["--resource-group", resource_group, "--name", app, "--revision", revision]
        run_az(["containerapp", "revision", "deactivate", *args])
        deadline = clock() + timeout_seconds
        while True:
            properties = run_az(["containerapp", "revision", "show", *args])["properties"]
            if not _revision_is_live(properties):
                break
            if clock() >= deadline:
                raise RuntimeError(f"{app}: old dispatch replica did not drain")
            sleep(5)
    # Detect a rollout concurrent with the exclusion operation.
    apps = run_az(["containerapp", "list", "--resource-group", resource_group, "--query", "[].name"])
    if not isinstance(apps, list) or not all(isinstance(app, str) for app in apps):
        raise ValueError("Invalid application inventory")
    for member in MEMBERS:
        app = f"ca-demo-{member}"
        if app not in apps:
            continue
        revisions = run_az(
            [
                "containerapp",
                "revision",
                "list",
                "--resource-group",
                resource_group,
                "--name",
                app,
                "--all",
            ]
        )
        if _old_dispatch_revisions(revisions, images[member]):
            raise RuntimeError("Old dispatch revision appeared during rollout exclusion")
    return {
        "schema": "waooaw.wc134-dispatch-rollout/v1",
        "status": "passed",
        "retired": [{"app": app, "revision": revision} for app, revision in plans],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--tfvars", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = quiesce(args.resource_group, json.loads(args.tfvars.read_text())["image_digests"])
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

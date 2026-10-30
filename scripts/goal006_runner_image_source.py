#!/usr/bin/env python3
"""Resolve the broker/cleanup control image from the runner-stack ACR, falling back to GHCR (WC-128).

The runner jobs keep the GHCR blueprint digest as their declared image, so stack validation and
execution guards are unchanged. Only the per-execution control image is redirected to the same digest
in the runner-stack ACR, which sits next to the Container Apps environment and avoids slow GHCR pulls.

Modes:
  publish  copy the digest into the runner ACR when missing (control-plane identity with AcrPush).
  verify   use the runner ACR only when the digest is already complete there (cleanup identity, AcrPull).

Any registry, job-configuration, or copy problem falls back to the GHCR blueprint image; this step never
blocks broker or cleanup start.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from goal006_image_mirror import (
    MirrorError,
    Runner,
    copy_image,
    is_complete,
    parse_source,
    run_command,
    target_reference,
)

RUNNER_LOGIN_SERVER = re.compile(r"^acrwaooawrun(?:demo|uat|prod)[0-9a-f]{6}[.]azurecr[.]io$")
PULL_IDENTITY_SUFFIX = re.compile(
    r"/providers/Microsoft[.]ManagedIdentity/userAssignedIdentities/goal006-(?:demo|uat|prod)-runner-image-pull-identity$",
    re.IGNORECASE,
)
MODES = ("publish", "verify")


def job_pulls_from(job: Mapping[str, Any], login_server: str) -> bool:
    """True when the job declares the runner ACR with the stack image-pull identity it also carries."""
    properties = job.get("properties") or {}
    registries = (properties.get("configuration") or {}).get("registries") or []
    identities = {key.lower() for key in ((job.get("identity") or {}).get("userAssignedIdentities") or {})}
    for registry in registries:
        if not isinstance(registry, Mapping):
            continue
        identity = str(registry.get("identity") or "")
        if (
            str(registry.get("server") or "").lower() == login_server
            and PULL_IDENTITY_SUFFIX.search(identity)
            and identity.lower() in identities
        ):
            return True
    return False


def resolve_control_image(
    *,
    mode: str,
    blueprint_image: str,
    login_server: str,
    job: Mapping[str, Any],
    registry_ready: bool,
    run: Runner = run_command,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError("mode must be publish or verify")
    parse_source(blueprint_image)
    started = clock()
    evidence: dict[str, Any] = {
        "mode": mode,
        "blueprint_image": blueprint_image,
        "control_image": blueprint_image,
        "source": "ghcr",
        "registry_server": "",
        "copied": False,
        "fallback_reason": "",
    }
    try:
        if RUNNER_LOGIN_SERVER.fullmatch(login_server) is None:
            raise ValueError("login server must be the runner-stack WAOOAW ACR")
        if not registry_ready:
            raise MirrorError("runner ACR is not reachable with this identity; redeploy the runner stack")
        if not job_pulls_from(job, login_server):
            raise MirrorError("job does not declare the runner ACR with the stack image-pull identity")
        if mode == "publish":
            record = copy_image(login_server, blueprint_image, run, sleep=sleep)
            evidence["copied"] = bool(record["copied"])
        elif not is_complete(login_server, blueprint_image, run):
            raise MirrorError("runner digest is not present in the runner ACR")
    except (MirrorError, ValueError, subprocess.TimeoutExpired) as error:
        evidence["fallback_reason"] = str(error)
    else:
        evidence.update(
            {
                "control_image": target_reference(login_server, blueprint_image),
                "source": "runner-acr",
                "registry_server": login_server,
            }
        )
    evidence["seconds"] = round(clock() - started, 1)
    return evidence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--blueprint-image", required=True)
    parser.add_argument("--login-server", required=True)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--registry-ready", choices=("true", "false"), default="false")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    job = json.loads(arguments.job.read_text(encoding="utf-8"))
    evidence = resolve_control_image(
        mode=arguments.mode,
        blueprint_image=arguments.blueprint_image,
        login_server=arguments.login_server.lower(),
        job=job,
        registry_ready=arguments.registry_ready == "true",
    )
    arguments.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(evidence["control_image"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

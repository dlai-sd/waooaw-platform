#!/usr/bin/env python3
"""Validate commit-bound pre-PR runtime lifecycle evidence for applicable diffs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RUNTIME_EVIDENCE_SECTION = re.compile(
    r"^## Pre-PR Runtime Evidence\s*$\n.*?```json\s*\n(?P<json>.*?)\n```",
    re.MULTILINE | re.DOTALL,
)
RUNTIME_GATE_PATHS = (
    "src/professional-runtime/",
    "infrastructure/terraform/phase2/modules/workload/",
    "scripts/goal006_verify_deployment.sh",
    "scripts/run_goal006_local_azure_verification.sh",
    "scripts/run_goal006_runtime_lifecycle_gate.sh",
)
DIGEST_IMAGE = re.compile(r".+@sha256:[0-9a-f]{64}$")
SHA256 = re.compile(r"[0-9a-f]{64}$")


def runtime_gate_required(changed_files: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix) for path in changed_files for prefix in RUNTIME_GATE_PATHS)


def validate_runtime_evidence(body: str, head: str, required: bool) -> list[str]:
    match = RUNTIME_EVIDENCE_SECTION.search(body)
    if match is None:
        return ["RUNTIME_EVIDENCE_MISSING: run scripts/prepare_pr_body.py"] if required else []
    try:
        evidence = json.loads(match.group("json"))
    except json.JSONDecodeError as error:
        return [f"RUNTIME_EVIDENCE_INVALID_JSON: {error}"]

    violations: list[str] = []
    expected = {
        "schema": "waooaw.goal006-runtime-lifecycle/v1",
        "passed": True,
        "commit_sha": head,
        "initial_http_status": 503,
        "recovered_http_status": 200,
    }
    for field, value in expected.items():
        if evidence.get(field) != value:
            violations.append(f"RUNTIME_EVIDENCE_INVALID: {field} must equal {value!r}")
    if evidence.get("initial_health", {}).get("temporalConnected") is not False:
        violations.append("RUNTIME_EVIDENCE_INVALID: initial Temporal state must be disconnected")
    if evidence.get("recovered_health", {}).get("temporalConnected") is not True:
        violations.append("RUNTIME_EVIDENCE_INVALID: recovered Temporal state must be connected")
    for field in ("initial_health", "recovered_health"):
        if evidence.get(field, {}).get("constitutionalEngineReachable") is not True:
            violations.append(f"RUNTIME_EVIDENCE_INVALID: {field} must report CE reachable")
    for field in ("temporal_image", "postgres_image"):
        if DIGEST_IMAGE.fullmatch(str(evidence.get(field, ""))) is None:
            violations.append(f"RUNTIME_EVIDENCE_INVALID: {field} must be digest-pinned")
    if not str(evidence.get("runtime_image", "")).endswith(f":{head[:12]}"):
        violations.append("RUNTIME_EVIDENCE_INVALID: runtime image must identify the reviewed commit")
    if SHA256.fullmatch(str(evidence.get("professional_runtime_log_sha256", ""))) is None:
        violations.append("RUNTIME_EVIDENCE_INVALID: runtime log SHA-256 is required")
    return violations


def changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(  # noqa: S603
        ["git", "diff", "--name-only", f"{base}..{head}"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-body-file", required=True, type=Path)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    arguments = parser.parse_args()
    try:
        required = runtime_gate_required(changed_files(arguments.base, arguments.head))
        violations = validate_runtime_evidence(
            arguments.pr_body_file.read_text(encoding="utf-8"),
            arguments.head,
            required,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        violations = [f"RUNTIME_EVIDENCE_UNREADABLE: {error}"]
    if violations:
        print("Runtime lifecycle evidence validation failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("Runtime lifecycle evidence validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

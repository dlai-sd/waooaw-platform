#!/usr/bin/env python3
"""Validate commit-bound pre-PR runtime lifecycle evidence for applicable diffs."""

from __future__ import annotations

import argparse
import json
import re
import shutil
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


def runtime_evidence_commit(body: str) -> str | None:
    match = RUNTIME_EVIDENCE_SECTION.search(body)
    if match is None:
        return None
    try:
        evidence = json.loads(match.group("json"))
    except json.JSONDecodeError:
        return None
    commit_sha = evidence.get("commit_sha")
    return commit_sha if isinstance(commit_sha, str) else None


def validate_runtime_evidence(
    body: str,
    head: str,
    required: bool,
    intervening_files: list[str] | None = None,
) -> list[str]:
    match = RUNTIME_EVIDENCE_SECTION.search(body)
    if match is None:
        return ["RUNTIME_EVIDENCE_MISSING: run scripts/prepare_pr_body.py"] if required else []
    try:
        evidence = json.loads(match.group("json"))
    except json.JSONDecodeError as error:
        return [f"RUNTIME_EVIDENCE_INVALID_JSON: {error}"]

    violations: list[str] = []
    evidence_head = str(evidence.get("commit_sha", ""))
    expected = {
        "schema": "waooaw.goal006-runtime-lifecycle/v1",
        "passed": True,
        "initial_http_status": 503,
        "recovered_http_status": 200,
        "interrupted_http_status": 503,
        "restart_recovered_http_status": 200,
    }
    for field, value in expected.items():
        if evidence.get(field) != value:
            violations.append(f"RUNTIME_EVIDENCE_INVALID: {field} must equal {value!r}")
    if evidence_head != head and (intervening_files is None or runtime_gate_required(intervening_files)):
        violations.append(f"RUNTIME_EVIDENCE_INVALID: commit_sha must equal {head!r}")
    if evidence.get("initial_health", {}).get("temporalConnected") is not False:
        violations.append("RUNTIME_EVIDENCE_INVALID: initial Temporal state must be disconnected")
    if evidence.get("recovered_health", {}).get("temporalConnected") is not True:
        violations.append("RUNTIME_EVIDENCE_INVALID: recovered Temporal state must be connected")
    if evidence.get("interrupted_health", {}).get("temporalConnected") is not False:
        violations.append("RUNTIME_EVIDENCE_INVALID: interrupted Temporal state must be disconnected")
    if evidence.get("restart_recovered_health", {}).get("temporalConnected") is not True:
        violations.append("RUNTIME_EVIDENCE_INVALID: restart-recovered Temporal state must be connected")
    for field in ("initial_health", "recovered_health", "interrupted_health", "restart_recovered_health"):
        if evidence.get(field, {}).get("constitutionalEngineReachable") is not True:
            violations.append(f"RUNTIME_EVIDENCE_INVALID: {field} must report CE reachable")
    for field in ("temporal_image", "postgres_image"):
        if DIGEST_IMAGE.fullmatch(str(evidence.get(field, ""))) is None:
            violations.append(f"RUNTIME_EVIDENCE_INVALID: {field} must be digest-pinned")
    if not str(evidence.get("runtime_image", "")).endswith(f":{evidence_head[:12]}"):
        violations.append("RUNTIME_EVIDENCE_INVALID: runtime image must identify the evidence commit")
    if SHA256.fullmatch(str(evidence.get("professional_runtime_log_sha256", ""))) is None:
        violations.append("RUNTIME_EVIDENCE_INVALID: runtime log SHA-256 is required")
    return violations


def changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-c",
            f"safe.directory={Path.cwd().resolve()}",
            "diff",
            "--name-only",
            f"{base}..{head}",
        ],
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
        body = arguments.pr_body_file.read_text(encoding="utf-8")
        evidence_head = runtime_evidence_commit(body)
        intervening_files = None
        if evidence_head is not None and evidence_head != arguments.head:
            git_executable = shutil.which("git")
            if git_executable is None:
                raise OSError("git executable is required to validate runtime evidence ancestry")
            ancestor = subprocess.run(  # noqa: S603
                [
                    git_executable,
                    "-c",
                    f"safe.directory={Path.cwd().resolve()}",
                    "merge-base",
                    "--is-ancestor",
                    evidence_head,
                    arguments.head,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if ancestor.returncode == 0:
                intervening_files = changed_files(evidence_head, arguments.head)
        violations = validate_runtime_evidence(
            body,
            arguments.head,
            required,
            intervening_files,
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

#!/usr/bin/env python3
"""Create and validate exact-run Terraform plan provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FULL_SHA = re.compile(r"[0-9a-f]{40}$")
SCOPES = {"foundation", "workload"}
SCHEMA = "waooaw.terraform-plan-provenance/v1"


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def create_provenance(
    *,
    environment: str,
    release_sha: str,
    release_run_id: str,
    workflow_run_id: str,
    workflow_run_attempt: str,
    scope: str,
    terraform_root: str,
    backend_key: str,
    plan_json: Path,
    plan_binary: Path,
    policy_result: Path,
    state: Path,
) -> dict[str, Any]:
    if environment not in {"demo", "uat"}:
        raise ValueError("plan provenance is supported only for Demo and UAT")
    if scope not in SCOPES:
        raise ValueError("plan provenance scope must be foundation or workload")
    if FULL_SHA.fullmatch(release_sha) is None:
        raise ValueError("release SHA must be a full lowercase Git SHA")
    if not all(value.isdigit() for value in (release_run_id, workflow_run_id, workflow_run_attempt)):
        raise ValueError("run identities must be numeric")
    expected_root = f"infrastructure/terraform/phase2/environments/{environment}/{scope}"
    expected_backend_key = f"goal006/{environment}/{scope}.tfstate"
    if terraform_root != expected_root:
        raise ValueError(f"{scope} Terraform root is not environment-exact")
    if backend_key != expected_backend_key:
        raise ValueError(f"{scope} backend key is not environment-exact")

    plan = load_json(plan_json)
    if not isinstance(plan, dict) or not isinstance(plan.get("resource_changes"), list):
        raise ValueError(f"{scope} plan is not a Terraform JSON plan")
    policy = load_json(policy_result)
    expected_policy = {
        "schema": "waooaw.terraform-plan-policy-result/v1",
        "status": "PASS",
        "scope": scope,
        "transition": "standard",
        "plan_json_sha256": file_digest(plan_json),
        "destructive_changes": 0,
    }
    if policy != expected_policy:
        raise ValueError(f"{scope} plan policy result is invalid")
    state_record = load_json(state)
    lineage = state_record.get("lineage") if isinstance(state_record, dict) else None
    serial = state_record.get("serial") if isinstance(state_record, dict) else None
    if not isinstance(lineage, str) or not lineage.strip() or not isinstance(serial, int) or serial < 0:
        raise ValueError(f"{scope} Terraform state lineage or serial is invalid")

    return {
        "schema": SCHEMA,
        "environment": environment,
        "release_sha": release_sha,
        "release_run_id": release_run_id,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": workflow_run_attempt,
        "scope": scope,
        "terraform_root": terraform_root,
        "backend_key": backend_key,
        "state_lineage": lineage,
        "state_serial": serial,
        "plan_json_sha256": file_digest(plan_json),
        "plan_binary_sha256": file_digest(plan_binary),
        "policy_result_sha256": file_digest(policy_result),
    }


def validate_provenance(
    record: Any,
    *,
    environment: str,
    release_sha: str,
    release_run_id: str,
    workflow_run_id: str,
    workflow_run_attempt: str,
    scope: str,
    plan_json: Path,
    plan_binary: Path,
    policy_result: Path,
) -> None:
    if not isinstance(record, dict):
        raise ValueError(f"{scope} plan provenance must be an object")
    expected = {
        "schema": SCHEMA,
        "environment": environment,
        "release_sha": release_sha,
        "release_run_id": release_run_id,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": workflow_run_attempt,
        "scope": scope,
        "terraform_root": f"infrastructure/terraform/phase2/environments/{environment}/{scope}",
        "backend_key": f"goal006/{environment}/{scope}.tfstate",
        "plan_json_sha256": file_digest(plan_json),
        "plan_binary_sha256": file_digest(plan_binary),
        "policy_result_sha256": file_digest(policy_result),
    }
    mismatches = sorted(key for key, value in expected.items() if record.get(key) != value)
    if mismatches:
        raise ValueError(f"{scope} plan provenance mismatch: {mismatches}")
    if not isinstance(record.get("state_lineage"), str) or not record["state_lineage"].strip():
        raise ValueError(f"{scope} plan provenance state lineage is invalid")
    if not isinstance(record.get("state_serial"), int) or record["state_serial"] < 0:
        raise ValueError(f"{scope} plan provenance state serial is invalid")
    if set(record) != set(expected) | {"state_lineage", "state_serial"}:
        raise ValueError(f"{scope} plan provenance fields are not exact")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--release-run-id", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--workflow-run-attempt", required=True)
    parser.add_argument("--scope", required=True, choices=sorted(SCOPES))
    parser.add_argument("--terraform-root", required=True)
    parser.add_argument("--backend-key", required=True)
    parser.add_argument("--plan-json", required=True, type=Path)
    parser.add_argument("--plan-binary", required=True, type=Path)
    parser.add_argument("--policy-result", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    record = create_provenance(
        environment=arguments.environment,
        release_sha=arguments.release_sha,
        release_run_id=arguments.release_run_id,
        workflow_run_id=arguments.workflow_run_id,
        workflow_run_attempt=arguments.workflow_run_attempt,
        scope=arguments.scope,
        terraform_root=arguments.terraform_root,
        backend_key=arguments.backend_key,
        plan_json=arguments.plan_json,
        plan_binary=arguments.plan_binary,
        policy_result=arguments.policy_result,
        state=arguments.state,
    )
    arguments.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

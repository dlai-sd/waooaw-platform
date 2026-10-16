#!/usr/bin/env python3
"""Generate the internal WC-124 activation bundle for an apply run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FULL_SHA = re.compile(r"[0-9a-f]{40}$")


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_set_digest(paths: list[Path]) -> str:
    names = [path.as_posix() for path in paths]
    if len(names) != len(set(names)):
        raise ValueError("deployment bundle file identities must be unique")
    if not paths:
        raise ValueError("deployment bundle file set must not be empty")
    entries = [
        {
            "path": path.as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(paths, key=lambda item: item.as_posix())
    ]
    return canonical_digest(entries)


def create_bundle(
    *,
    environment: str,
    release_sha: str,
    release_run_id: str,
    actor: str,
    workflow_run_id: str,
    workflow_run_attempt: str,
    lease_expiry: str,
    foundation_plan: Path,
    workload_plan: Path,
    secret_catalog: Path,
    configuration: Path,
    dependency_files: list[Path],
    migration_files: list[Path],
    schema_files: list[Path],
) -> dict[str, Any]:
    if environment not in {"demo", "uat"}:
        raise ValueError("apply bundles are supported only for Demo and UAT")
    if FULL_SHA.fullmatch(release_sha) is None:
        raise ValueError("release SHA must be a full lowercase Git SHA")
    if not release_run_id.isdigit() or not workflow_run_id.isdigit() or not workflow_run_attempt.isdigit():
        raise ValueError("run identities must be numeric")
    if not actor.strip() or not lease_expiry.strip():
        raise ValueError("actor and lease expiry are required")

    foundation = load_json(foundation_plan)
    workload = load_json(workload_plan)
    catalog = load_json(secret_catalog)
    config = load_json(configuration)
    for name, plan in (("foundation", foundation), ("workload", workload)):
        if not isinstance(plan, dict) or not isinstance(plan.get("resource_changes"), list):
            raise ValueError(f"{name} plan is not a Terraform JSON plan")

    plan_digest = canonical_digest(
        {
            "foundation": foundation,
            "workload": workload,
        }
    )
    secret_catalog_digest = canonical_digest(catalog)
    tuple_digests = {
        "configuration": canonical_digest(config),
        "dependency": file_set_digest(dependency_files),
        "migration": file_set_digest(migration_files),
        "release": "sha256:" + hashlib.sha256(release_sha.encode("ascii")).hexdigest(),
        "schema": file_set_digest(schema_files),
    }
    authorization = {
        "founder_action_authority": f"FA-GITHUB-WORKFLOW-DISPATCH-{workflow_run_id}-{actor}",
        "runner_execution_identity": f"id-waooaw-{environment}-deployment-writer",
        "release_sha": release_sha,
        "plan_digest": plan_digest,
        "secret_catalog_digest": secret_catalog_digest,
        "lease_id": f"wc124-{environment}-{workflow_run_id}-{workflow_run_attempt}",
        "lease_expiry": lease_expiry,
    }
    bundle: dict[str, Any] = {
        "schema": "waooaw.wc124-deployment-activation-bundle/v1",
        "environment": environment,
        "release_run_id": release_run_id,
        "workflow_run_id": workflow_run_id,
        "workflow_run_attempt": workflow_run_attempt,
        "authorization": authorization,
        "tuple_digests": tuple_digests,
    }
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--release-run-id", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--workflow-run-attempt", required=True)
    parser.add_argument("--lease-expiry", required=True)
    parser.add_argument("--foundation-plan", required=True, type=Path)
    parser.add_argument("--workload-plan", required=True, type=Path)
    parser.add_argument("--secret-catalog", required=True, type=Path)
    parser.add_argument("--configuration", required=True, type=Path)
    parser.add_argument("--dependency-file", action="append", required=True, type=Path)
    parser.add_argument("--migration-file", action="append", required=True, type=Path)
    parser.add_argument("--schema-file", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    bundle = create_bundle(
        environment=arguments.environment,
        release_sha=arguments.release_sha,
        release_run_id=arguments.release_run_id,
        actor=arguments.actor,
        workflow_run_id=arguments.workflow_run_id,
        workflow_run_attempt=arguments.workflow_run_attempt,
        lease_expiry=arguments.lease_expiry,
        foundation_plan=arguments.foundation_plan,
        workload_plan=arguments.workload_plan,
        secret_catalog=arguments.secret_catalog,
        configuration=arguments.configuration,
        dependency_files=arguments.dependency_file,
        migration_files=arguments.migration_file,
        schema_files=arguments.schema_file,
    )
    arguments.output.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

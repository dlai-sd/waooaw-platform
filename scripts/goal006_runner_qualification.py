#!/usr/bin/env python3
"""Qualify GOAL-006 private Storage and Terraform paths from an ephemeral runner."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import subprocess
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class QualificationError(RuntimeError):
    """Fail-closed private-path qualification error."""


PROBE_NAME = re.compile(
    r"^goal006/(?P<environment>demo|uat|prod)/qualification/"
    r"goal006-(?P=environment)-(?P<run_id>[1-9][0-9]*)-(?P<attempt>[1-9][0-9]*)[.]json$"
)
STALE_PROBE_AGE = timedelta(hours=1)


def resolve_private_addresses(hostname: str) -> list[str]:
    try:
        addresses = sorted(
            {item[4][0] for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)}
        )
    except socket.gaierror as error:
        raise QualificationError(f"private DNS resolution failed for {hostname}") from error
    if not addresses or any(not ipaddress.ip_address(value).is_private for value in addresses):
        raise QualificationError(f"public or empty DNS answer rejected for {hostname}")
    return addresses


def _run(arguments: Sequence[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(  # noqa: S603
        arguments,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        diagnostics = "\n".join(
            value.strip() for value in (result.stderr, result.stdout) if value.strip()
        )[-4000:]
        detail = f"\n{diagnostics}" if diagnostics else ""
        raise QualificationError(
            f"command failed ({result.returncode}): {arguments[0]} {arguments[1]}{detail}"
        )
    return result.stdout


def validate_workload_configuration(
    configuration: Mapping[str, Any], *, now: datetime | None = None
) -> None:
    observed_at = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
    if configuration.get("lease_state") != "ACTIVE":
        raise QualificationError("workload lease is not ACTIVE")
    try:
        issued_at = datetime.fromisoformat(
            str(configuration["lease_issued_at"]).replace("Z", "+00:00")
        )
        expires_at = datetime.fromisoformat(
            str(configuration["lease_expires_at"]).replace("Z", "+00:00")
        )
    except (KeyError, ValueError) as error:
        raise QualificationError("workload lease timestamps must be RFC3339") from error
    if issued_at.tzinfo is None or expires_at.tzinfo is None:
        raise QualificationError("workload lease timestamps must include timezone")
    issued_at = issued_at.astimezone(timezone.utc)
    expires_at = expires_at.astimezone(timezone.utc)
    if issued_at > observed_at or expires_at <= observed_at or expires_at <= issued_at:
        raise QualificationError("workload lease is not current")
    for field in ("planned_incremental_monthly_cost_inr", "cumulative_one_time_cost_inr"):
        value = configuration.get(field)
        if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
            raise QualificationError(f"{field} is invalid")
    evidence_digest = configuration.get("evidence_digest")
    if not isinstance(evidence_digest, str) or re.fullmatch(
        r"sha256:[0-9a-f]{64}", evidence_digest
    ) is None:
        raise QualificationError("evidence_digest is invalid")


def reconcile_stale_probe_blobs(
    storage: Sequence[str],
    common: Sequence[str],
    *,
    environment: str,
    container_name: str,
    current_blob: str,
    now: datetime | None = None,
) -> list[str]:
    observed_at = datetime.now(timezone.utc) if now is None else now.astimezone(timezone.utc)
    output = _run(
        [
            *storage,
            "list",
            "--container-name",
            container_name,
            "--prefix",
            f"goal006/{environment}/qualification/",
            "--output",
            "json",
            *common,
        ]
    )
    try:
        blobs = json.loads(output)
    except json.JSONDecodeError as error:
        raise QualificationError("stale probe inventory is invalid") from error
    if not isinstance(blobs, list):
        raise QualificationError("stale probe inventory is invalid")
    deleted: list[str] = []
    for blob in blobs:
        if not isinstance(blob, Mapping):
            raise QualificationError("stale probe inventory entry is invalid")
        name = str(blob.get("name", ""))
        if name == current_blob or PROBE_NAME.fullmatch(name) is None:
            continue
        properties = blob.get("properties")
        if not isinstance(properties, Mapping):
            raise QualificationError("stale probe properties are invalid")
        try:
            modified_at = datetime.fromisoformat(
                str(properties["lastModified"]).replace("Z", "+00:00")
            )
        except (KeyError, ValueError) as error:
            raise QualificationError("stale probe timestamp is invalid") from error
        if modified_at.tzinfo is None:
            raise QualificationError("stale probe timestamp lacks timezone")
        modified_at = modified_at.astimezone(timezone.utc)
        if observed_at - modified_at < STALE_PROBE_AGE:
            continue
        _run(
            [
                *storage,
                "delete",
                "--container-name",
                container_name,
                "--name",
                name,
                "--output",
                "none",
                *common,
            ]
        )
        deleted.append(name)
    return sorted(deleted)


def acquire_blob_lease(
    storage: Sequence[str],
    common: Sequence[str],
    *,
    container_name: str,
    blob_name: str,
) -> str:
    proposed_lease_id = str(uuid.uuid4())
    _run(
        [
            *storage,
            "lease",
            "acquire",
            "--blob-name",
            blob_name,
            "--container-name",
            container_name,
            "--lease-duration",
            "15",
            "--proposed-lease-id",
            proposed_lease_id,
            "--output",
            "none",
            *common,
        ]
    )
    return proposed_lease_id


def release_blob_lease(
    storage: Sequence[str],
    common: Sequence[str],
    *,
    container_name: str,
    blob_name: str,
    lease_id: str,
) -> None:
    _run(
        [
            *storage,
            "lease",
            "release",
            "--blob-name",
            blob_name,
            "--container-name",
            container_name,
            "--lease-id",
            lease_id,
            "--output",
            "none",
            *common,
        ]
    )


def qualify(
    *,
    environment: str,
    correlation: str,
    account_name: str,
    state_container: str,
    config_container: str,
    config_blob: str,
    terraform_root: Path,
    output_directory: Path,
) -> dict[str, Any]:
    if environment not in {"demo", "uat", "prod"}:
        raise QualificationError("environment is invalid")
    if correlation.replace(":", "-") != correlation.replace(":", "-").lower():
        raise QualificationError("correlation is invalid")
    output_directory = output_directory.resolve()
    terraform_root = terraform_root.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    hostname = f"{account_name}.blob.core.windows.net"
    addresses = resolve_private_addresses(hostname)
    configuration_path = output_directory / "workload-configuration.json"
    probe_path = output_directory / "storage-probe.json"
    plan_path = output_directory / "foundation.tfplan"
    probe_blob = f"goal006/{environment}/qualification/{correlation.replace(':', '-')}.json"
    probe_path.write_text(
        json.dumps(
            {
                "schema": "waooaw.goal006-private-path-probe/v1",
                "environment": environment,
                "correlation_id": correlation,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    storage = ["az", "storage", "blob"]
    common = ["--account-name", account_name, "--auth-mode", "login", "--only-show-errors"]
    _run(
        [
            *storage,
            "download",
            "--container-name",
            config_container,
            "--name",
            config_blob,
            "--file",
            str(configuration_path),
            "--overwrite",
            "--output",
            "none",
            *common,
        ]
    )
    try:
        configuration = json.loads(configuration_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise QualificationError("workload configuration is invalid") from error
    if not isinstance(configuration, Mapping):
        raise QualificationError("workload configuration is invalid")
    validate_workload_configuration(configuration)
    reconciled_probe_blobs = reconcile_stale_probe_blobs(
        storage,
        common,
        environment=environment,
        container_name=state_container,
        current_blob=probe_blob,
    )
    uploaded = False
    lease_id = ""
    operation_error: Exception | None = None
    try:
        _run(
            [
                *storage,
                "upload",
                "--container-name",
                state_container,
                "--name",
                probe_blob,
                "--file",
                str(probe_path),
                "--overwrite",
                "false",
                "--output",
                "none",
                *common,
            ]
        )
        uploaded = True
        _run(
            [
                *storage,
                "show",
                "--container-name",
                state_container,
                "--name",
                probe_blob,
                "--output",
                "json",
                *common,
            ]
        )
        lease_id = acquire_blob_lease(
            storage,
            common,
            container_name=state_container,
            blob_name=probe_blob,
        )
        release_blob_lease(
            storage,
            common,
            container_name=state_container,
            blob_name=probe_blob,
            lease_id=lease_id,
        )
        lease_id = ""
        _run(
            [
                "terraform",
                "init",
                "-input=false",
                f"-backend-config=resource_group_name={os.environ['TFSTATE_RESOURCE_GROUP']}",
                f"-backend-config=storage_account_name={account_name}",
                f"-backend-config=container_name={state_container}",
                "-backend-config=use_oidc=true",
                "-backend-config=use_azuread_auth=true",
            ],
            cwd=terraform_root,
        )
        _run(["terraform", "validate"], cwd=terraform_root)
        _run(
            [
                "terraform",
                "plan",
                "-input=false",
                "-lock-timeout=5m",
                (
                    "-var=tfstate_storage_account_id=/subscriptions/"
                    f"{os.environ['ARM_SUBSCRIPTION_ID']}/resourceGroups/"
                    f"{os.environ['TFSTATE_RESOURCE_GROUP']}/providers/"
                    f"Microsoft.Storage/storageAccounts/{account_name}"
                ),
                f"-out={plan_path}",
            ],
            cwd=terraform_root,
        )
    except Exception as error:
        operation_error = error
    cleanup_errors: list[QualificationError] = []
    if lease_id:
        try:
            release_blob_lease(
                storage,
                common,
                container_name=state_container,
                blob_name=probe_blob,
                lease_id=lease_id,
            )
        except QualificationError as error:
            cleanup_errors.append(error)
    if uploaded:
        try:
            _run(
                [
                    *storage,
                    "delete",
                    "--container-name",
                    state_container,
                    "--name",
                    probe_blob,
                    "--output",
                    "none",
                    *common,
                ]
            )
        except QualificationError as error:
            cleanup_errors.append(error)
    if operation_error is not None:
        if cleanup_errors:
            details = "; ".join(str(error) for error in cleanup_errors)
            raise QualificationError(f"{operation_error}; cleanup failed: {details}") from operation_error
        raise operation_error
    if cleanup_errors:
        details = "; ".join(str(error) for error in cleanup_errors)
        raise QualificationError(f"cleanup failed: {details}")
    return {
        "schema": "waooaw.goal006-private-path-qualification/v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "environment": environment,
        "correlation_id": correlation,
        "storage_hostname": hostname,
        "resolved_private_addresses": addresses,
        "configuration_blob": f"{config_container}/{config_blob}",
        "state_probe_blob": probe_blob,
        "stale_probe_blobs_deleted": reconciled_probe_blobs,
        "configuration_lease_valid": True,
        "configuration_read": True,
        "state_create_read_lock_delete": True,
        "terraform_init_validate_plan": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("demo", "uat", "prod"), required=True)
    parser.add_argument("--correlation", required=True)
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--state-container", required=True)
    parser.add_argument("--config-container", required=True)
    parser.add_argument("--config-blob", required=True)
    parser.add_argument("--terraform-root", required=True, type=Path)
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = qualify(
        environment=args.environment,
        correlation=args.correlation,
        account_name=args.account_name,
        state_container=args.state_container,
        config_container=args.config_container,
        config_blob=args.config_blob,
        terraform_root=args.terraform_root,
        output_directory=args.output_directory,
    )
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"qualified": True, "correlation_id": args.correlation}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
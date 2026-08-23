#!/usr/bin/env python3
"""Qualify GOAL-006 private Storage and Terraform paths from an ephemeral runner."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import subprocess
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class QualificationError(RuntimeError):
    """Fail-closed private-path qualification error."""


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
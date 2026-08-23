"""Contracts for private runner Storage and Terraform qualification."""

from __future__ import annotations

import json
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.goal006_runner_qualification import (
    QualificationError,
    _run,
    qualify,
    reconcile_stale_probe_blobs,
    resolve_private_addresses,
    validate_workload_configuration,
)


def valid_configuration() -> dict:
    return {
        "lease_state": "ACTIVE",
        "lease_issued_at": "2020-01-01T00:00:00Z",
        "lease_expires_at": "2099-01-01T00:00:00Z",
        "planned_incremental_monthly_cost_inr": 1000,
        "cumulative_one_time_cost_inr": 1000,
        "evidence_digest": "sha256:" + "a" * 64,
    }


def test_private_dns_accepts_only_private_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.70.0.36", 443))
        ],
    )
    assert resolve_private_addresses("state.blob.core.windows.net") == ["10.70.0.36"]


@pytest.mark.parametrize("address", ["20.60.1.2", "8.8.8.8"])
def test_public_dns_answer_fails_closed(
    monkeypatch: pytest.MonkeyPatch, address: str
) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))
        ],
    )
    with pytest.raises(QualificationError, match="public or empty"):
        resolve_private_addresses("state.blob.core.windows.net")


def test_dns_failure_is_not_inferred_as_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise socket.gaierror("NXDOMAIN")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(QualificationError, match="resolution failed"):
        resolve_private_addresses("state.blob.core.windows.net")


def test_expired_workload_configuration_fails_closed() -> None:
    configuration = valid_configuration()
    configuration["lease_expires_at"] = "2026-08-23T09:00:00Z"
    with pytest.raises(QualificationError, match="not current"):
        validate_workload_configuration(
            configuration, now=datetime(2026, 8, 23, 10, tzinfo=timezone.utc)
        )


def test_timezone_naive_workload_configuration_fails_closed() -> None:
    configuration = valid_configuration()
    configuration["lease_expires_at"] = "2026-08-23T12:00:00"
    with pytest.raises(QualificationError, match="timezone"):
        validate_workload_configuration(
            configuration, now=datetime(2026, 8, 23, 10, tzinfo=timezone.utc)
        )


def test_only_old_correlation_shaped_probes_are_reconciled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def run(arguments, *, cwd=None):
        commands.append(arguments)
        if "list" in arguments:
            return json.dumps(
                [
                    {
                        "name": "goal006/demo/qualification/goal006-demo-100-1.json",
                        "properties": {"lastModified": "2026-08-23T08:00:00Z"},
                    },
                    {
                        "name": "goal006/demo/qualification/goal006-demo-200-1.json",
                        "properties": {"lastModified": "2026-08-23T09:30:00Z"},
                    },
                    {
                        "name": "goal006/demo/qualification/not-a-probe.json",
                        "properties": {"lastModified": "2026-08-20T08:00:00Z"},
                    },
                ]
            )
        return ""

    monkeypatch.setattr("scripts.goal006_runner_qualification._run", run)
    deleted = reconcile_stale_probe_blobs(
        ["az", "storage", "blob"],
        ["--account-name", "state"],
        environment="demo",
        container_name="tfstate",
        current_blob="goal006/demo/qualification/goal006-demo-300-1.json",
        now=datetime(2026, 8, 23, 10, tzinfo=timezone.utc),
    )
    assert deleted == ["goal006/demo/qualification/goal006-demo-100-1.json"]
    assert [command[command.index("--name") + 1] for command in commands if "delete" in command] == deleted


def test_terraform_plan_uses_absolute_evidence_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    commands: list[tuple[list[str], Path | None]] = []

    def run(arguments, *, cwd=None):
        commands.append((arguments, cwd))
        if "download" in arguments:
            Path(arguments[arguments.index("--file") + 1]).write_text(
                json.dumps(valid_configuration()), encoding="utf-8"
            )
        if "list" in arguments:
            return "[]"
        return ""

    monkeypatch.setattr(
        "scripts.goal006_runner_qualification.resolve_private_addresses",
        lambda hostname: ["10.70.0.36"],
    )
    monkeypatch.setattr("scripts.goal006_runner_qualification._run", run)
    monkeypatch.setenv("ARM_SUBSCRIPTION_ID", "subscription")
    monkeypatch.setenv("TFSTATE_RESOURCE_GROUP", "waooaw-platform-rg")
    terraform_root = tmp_path / "terraform"
    terraform_root.mkdir()
    output_directory = tmp_path / "evidence"

    record = qualify(
        environment="demo",
        correlation="goal006:demo:123:1",
        account_name="state",
        state_container="tfstate",
        config_container="configuration",
        config_blob="demo/configuration.json",
        terraform_root=terraform_root,
        output_directory=output_directory,
    )

    plan = next(arguments for arguments, _ in commands if arguments[:2] == ["terraform", "plan"])
    acquire = next(arguments for arguments, _ in commands if "acquire" in arguments)
    release = next(arguments for arguments, _ in commands if "release" in arguments)
    proposed_lease_id = acquire[acquire.index("--proposed-lease-id") + 1]
    assert release[release.index("--lease-id") + 1] == proposed_lease_id
    assert (
        "-var=tfstate_storage_account_id=/subscriptions/subscription/resourceGroups/"
        "waooaw-platform-rg/providers/Microsoft.Storage/storageAccounts/state"
    ) in plan
    assert f"-out={output_directory.resolve() / 'foundation.tfplan'}" in plan
    assert record["terraform_init_validate_plan"] is True


def test_command_failure_preserves_bounded_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 2, stdout="provider detail", stderr="authorization failed"
        ),
    )

    with pytest.raises(QualificationError) as failure:
        _run(["terraform", "plan"])

    message = str(failure.value)
    assert "command failed (2): terraform plan" in message
    assert "authorization failed" in message
    assert "provider detail" in message


def test_probe_delete_is_attempted_when_lease_release_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    commands: list[list[str]] = []

    def run(arguments, *, cwd=None):
        commands.append(arguments)
        if "download" in arguments:
            Path(arguments[arguments.index("--file") + 1]).write_text(
                json.dumps(valid_configuration()), encoding="utf-8"
            )
        if "list" in arguments:
            return "[]"
        if "release" in arguments:
            raise QualificationError("lease release failed")
        return ""

    monkeypatch.setattr(
        "scripts.goal006_runner_qualification.resolve_private_addresses",
        lambda hostname: ["10.70.0.36"],
    )
    monkeypatch.setattr("scripts.goal006_runner_qualification._run", run)
    monkeypatch.setenv("ARM_SUBSCRIPTION_ID", "subscription")
    monkeypatch.setenv("TFSTATE_RESOURCE_GROUP", "waooaw-platform-rg")
    terraform_root = tmp_path / "terraform"
    terraform_root.mkdir()

    with pytest.raises(QualificationError, match="lease release failed"):
        qualify(
            environment="demo",
            correlation="goal006:demo:123:1",
            account_name="state",
            state_container="tfstate",
            config_container="configuration",
            config_blob="demo/configuration.json",
            terraform_root=terraform_root,
            output_directory=tmp_path / "evidence",
        )

    assert any("delete" in arguments for arguments in commands)
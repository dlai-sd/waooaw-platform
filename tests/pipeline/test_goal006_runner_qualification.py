"""Contracts for private runner Storage and Terraform qualification."""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path

import pytest

from scripts.goal006_runner_qualification import (
    QualificationError,
    _run,
    qualify,
    resolve_private_addresses,
)


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


def test_terraform_plan_uses_absolute_evidence_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    commands: list[tuple[list[str], Path | None]] = []

    def run(arguments, *, cwd=None):
        commands.append((arguments, cwd))
        return "lease-id" if arguments[1:3] == ["storage", "blob"] and "acquire" in arguments else ""

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
        if "acquire" in arguments:
            return "lease-id"
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
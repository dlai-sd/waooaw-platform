"""WC-106 exact-container readiness and unchanged-retry contracts."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from validation_control import catalog_execution
from validation_control.execution_contract import (
    UnchangedExecutionFailureError,
    assert_retry_allowed,
    binding_digest,
    evidence_path,
    execution_binding,
    orchestration_preflight,
    prepare_evidence,
    record_failure,
    safe_segment,
)


IMAGE_ID = "sha256:" + "b" * 64


def plan_and_node() -> tuple[dict[str, object], dict[str, object]]:
    node = {
        "gate_id": "test-python:professional-runtime",
        "runner_id": "python",
        "compose_service": "test-runner-python",
        "profile": "test-python",
        "command": "costly-command",
        "resources": {"docker_socket": True},
        "environment": [],
    }
    plan = {
        "schema": "waooaw.validation-execution-plan/v1",
        "head_sha": "a" * 40,
        "execution_namespace": "wc106-test",
        "nodes": [node],
    }
    return plan, node


def test_exact_container_preflight_precedes_costly_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plan, node = plan_and_node()
    (tmp_path / "test-results").mkdir()
    commands: list[list[str]] = []

    def execute(command: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append(command)
        environment = kwargs["env"]
        proof = tmp_path / environment["WC106_EVIDENCE_PATH"].removeprefix("/workspace/")
        proof.write_text(environment["WC106_EVIDENCE_TOKEN"] + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(catalog_execution.subprocess, "run", execute)

    result = catalog_execution.run_execution_preflight(
        plan, node, IMAGE_ID, "/usr/bin/docker", {}, tmp_path
    )

    assert result == 0
    assert len(commands) == 1
    assert commands[0][-1] == "sh scripts/validation_control/run_execution_contract.sh"
    assert evidence_path(tmp_path, "wc106-test", node["gate_id"]).is_file()


@pytest.mark.parametrize(
    "defect",
    (
        "missing-mount",
        "read-only-output",
        "read-only-cache",
        "wrong-user",
        "absent-docker-socket",
    ),
)
def test_environment_defects_stop_before_costly_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, defect: str
) -> None:
    plan, node = plan_and_node()
    (tmp_path / "test-results").mkdir()
    calls = 0

    def fail_preflight(*unused: object, **kwargs: object) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        assert kwargs["env"]["WC106_EVIDENCE_TOKEN"]
        return SimpleNamespace(returncode=71)

    monkeypatch.setattr(catalog_execution.subprocess, "run", fail_preflight)

    assert catalog_execution.run_execution_preflight(plan, node, IMAGE_ID, "docker", {}, tmp_path) == 71
    assert calls == 1, defect


@pytest.mark.parametrize("defect", ("stale-artifact", "container-only-output"))
def test_non_current_evidence_cannot_authorize_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, defect: str
) -> None:
    plan, node = plan_and_node()
    (tmp_path / "test-results").mkdir()
    stale = evidence_path(tmp_path, "wc106-test", node["gate_id"])
    stale.parent.mkdir(parents=True)
    stale.write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(
        catalog_execution.subprocess,
        "run",
        lambda *unused, **kwargs: SimpleNamespace(returncode=0),
    )

    assert catalog_execution.run_execution_preflight(plan, node, IMAGE_ID, "docker", {}, tmp_path) == 78
    assert not stale.exists(), defect


def test_unchanged_failure_is_blocked_until_bound_environment_changes(tmp_path: Path) -> None:
    plan, node = plan_and_node()
    results = tmp_path / "test-results"
    results.mkdir()
    digest = binding_digest(execution_binding(plan, node, IMAGE_ID, tmp_path))
    record_failure(tmp_path, node["gate_id"], digest, "read-only-cache")
    failure = json.loads(
        (tmp_path / "test-results/wc106/execution-failures/test-python-professional-runtime.json").read_text(
            encoding="utf-8"
        )
    )

    with pytest.raises(UnchangedExecutionFailureError):
        assert_retry_allowed(tmp_path, node["gate_id"], digest)
    assert len(failure["failure_fingerprint"]) == 64

    results.chmod(0o700)
    changed_digest = binding_digest(execution_binding(plan, node, IMAGE_ID, tmp_path))
    assert changed_digest != digest
    assert_retry_allowed(tmp_path, node["gate_id"], changed_digest)


def test_prepare_evidence_removes_stale_output(tmp_path: Path) -> None:
    path = evidence_path(tmp_path, "wc106-test", "gate")
    path.parent.mkdir(parents=True)
    path.write_text("stale\n", encoding="utf-8")

    prepared, token = prepare_evidence(tmp_path, "wc106-test", "gate", "digest")

    assert prepared == path
    assert not prepared.exists()
    assert len(token) == 64


def test_execution_identity_segments_cannot_escape_probe_roots() -> None:
    assert safe_segment("../../gate:name") == "gate-name"


def test_corrupt_failure_record_blocks_costly_retry(tmp_path: Path) -> None:
    path = tmp_path / "test-results/wc106/execution-failures/gate.json"
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(UnchangedExecutionFailureError, match="unreadable"):
        assert_retry_allowed(tmp_path, "gate", "digest")


def test_orchestration_preflight_rejects_unwritable_home_before_supply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    socket = tmp_path / "docker.sock"
    socket.touch()
    monkeypatch.setenv("HOME", str(tmp_path / "read-only-home"))
    original_access = catalog_execution.os.access

    def access(path: object, mode: int) -> bool:
        if Path(path) == tmp_path / "read-only-home":
            return False
        return original_access(path, mode)

    monkeypatch.setattr("validation_control.execution_contract.os.access", access)
    monkeypatch.setattr(Path, "is_socket", lambda self: self == socket)

    with pytest.raises(ValueError, match="HOME is not writable"):
        orchestration_preflight(tmp_path, socket)


def test_all_catalog_runners_use_writable_tmpfs_home() -> None:
    root = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text(encoding="utf-8"))

    for service in ("test-runner-python", "test-runner-dotnet", "test-runner-ts", "test-runner"):
        assert compose["services"][service]["environment"]["HOME"] == "/tmp/wc106-home"
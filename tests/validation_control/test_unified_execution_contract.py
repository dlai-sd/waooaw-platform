"""WC-106 exact-container readiness and unchanged-retry contracts."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
from threading import Barrier, Lock
from types import SimpleNamespace

import pytest
import yaml

from validation_control import catalog_execution
from validation_control.execution_contract import (
    UnchangedExecutionFailureError,
    assert_retry_allowed,
    binding_digest,
    disposable_cleanup_commands,
    evidence_is_current,
    evidence_path,
    execution_binding,
    orchestration_preflight,
    prepare_evidence,
    record_failure,
    resource_capacity_preflight,
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
        "compose_project": "wc109-test",
        "output_directory": "test-results/wc109/runs/wc109-test/test-python-professional-runtime",
    }
    plan = {
        "schema": "waooaw.validation-execution-plan/v1",
        "head_sha": "a" * 40,
        "execution_namespace": "wc106-test",
        "nodes": [node],
    }
    return plan, node


def proof_path(tmp_path: Path, node: dict[str, object], environment: dict[str, str]) -> Path:
    relative = environment["WC106_EVIDENCE_PATH"].removeprefix("/workspace/test-results/")
    return tmp_path / str(node["output_directory"]) / relative


def test_exact_container_preflight_precedes_costly_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plan, node = plan_and_node()
    (tmp_path / "test-results").mkdir()
    commands: list[list[str]] = []

    def execute(command: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append(command)
        environment = kwargs["env"]
        proof = proof_path(tmp_path, node, environment)
        proof.write_text(environment["WC106_EVIDENCE_TOKEN"] + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(catalog_execution.subprocess, "run", execute)

    result = catalog_execution.run_execution_preflight(plan, node, IMAGE_ID, "/usr/bin/docker", {}, tmp_path)

    assert result == 0
    assert len(commands) == 1
    assert commands[0][-1] == "sh scripts/validation_control/run_execution_contract.sh"
    assert evidence_path(
        tmp_path,
        "wc106-test",
        node["gate_id"],
        tmp_path / str(node["output_directory"]),
    ).is_file()


def test_host_gate_preflight_still_runs_in_declared_container(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plan, node = plan_and_node()
    node["execution"] = "host"
    (tmp_path / "test-results").mkdir()
    commands: list[list[str]] = []

    def execute(command: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append(command)
        environment = kwargs["env"]
        proof = proof_path(tmp_path, node, environment)
        proof.write_text(environment["WC106_EVIDENCE_TOKEN"] + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(catalog_execution.subprocess, "run", execute)

    result = catalog_execution.run_execution_preflight(plan, node, IMAGE_ID, "/usr/bin/docker", {}, tmp_path)

    assert result == 0
    assert commands[0][:5] == ["/usr/bin/docker", "compose", "--project-name", "wc109-test", "--profile"]
    assert commands[0][-1] == "sh scripts/validation_control/run_execution_contract.sh"


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
def test_environment_defects_stop_before_costly_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, defect: str) -> None:
    plan, node = plan_and_node()
    (tmp_path / "test-results").mkdir()
    calls = 0

    def fail_preflight(*unused: object, **kwargs: object) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        assert kwargs["env"]["WC106_EVIDENCE_TOKEN"]
        return SimpleNamespace(returncode=71)

    monkeypatch.setattr(catalog_execution.subprocess, "run", fail_preflight)

    assert catalog_execution.run_execution_preflight(plan, node, IMAGE_ID, "docker", {}, tmp_path) == 78
    assert calls == 1, defect


@pytest.mark.parametrize("defect", ("stale-artifact", "container-only-output"))
def test_non_current_evidence_cannot_authorize_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, defect: str) -> None:
    plan, node = plan_and_node()
    (tmp_path / "test-results").mkdir()
    stale = evidence_path(
        tmp_path,
        "wc106-test",
        node["gate_id"],
        tmp_path / str(node["output_directory"]),
    )
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
        (tmp_path / "test-results/wc106/execution-failures/test-python-professional-runtime.json").read_text(encoding="utf-8")
    )

    with pytest.raises(UnchangedExecutionFailureError):
        assert_retry_allowed(tmp_path, node["gate_id"], digest)
    assert len(failure["failure_fingerprint"]) == 64

    results.chmod(0o700)
    changed_digest = binding_digest(execution_binding(plan, node, IMAGE_ID, tmp_path))
    assert changed_digest != digest
    assert_retry_allowed(tmp_path, node["gate_id"], changed_digest)


def test_catalog_control_change_invalidates_execution_binding(tmp_path: Path) -> None:
    plan, node = plan_and_node()
    (tmp_path / "test-results").mkdir()
    catalog = tmp_path / "validation/engineering-validation.yaml"
    catalog.parent.mkdir()
    catalog.write_text("version: first\n", encoding="utf-8")
    first = binding_digest(execution_binding(plan, node, IMAGE_ID, tmp_path))

    catalog.write_text("version: second\n", encoding="utf-8")

    assert binding_digest(execution_binding(plan, node, IMAGE_ID, tmp_path)) != first


def test_prepare_evidence_removes_stale_output(tmp_path: Path) -> None:
    path = evidence_path(tmp_path, "wc106-test", "gate")
    path.parent.mkdir(parents=True)
    path.write_text("stale\n", encoding="utf-8")

    prepared, token = prepare_evidence(tmp_path, "wc106-test", "gate", "digest")

    assert prepared == path
    assert not prepared.exists()
    assert len(token) == 64


def test_host_atomically_republishes_read_only_container_proof(tmp_path: Path) -> None:
    path = tmp_path / "test-results/wc106/proof"
    path.parent.mkdir(parents=True)
    path.write_text("token\n", encoding="utf-8")
    path.chmod(0o444)

    assert evidence_is_current(path, "token") is True
    assert os.access(path, os.W_OK)


def test_hosted_action_stops_execution_contract_retries() -> None:
    root = Path(__file__).resolve().parents[2]
    action = yaml.safe_load((root / ".github/actions/run-validation-gate/action.yml").read_text(encoding="utf-8"))
    execution = next(step["run"] for step in action["runs"]["steps"] if step.get("id") == "execution")
    syntax = subprocess.run(["bash", "-n"], input=execution, text=True, capture_output=True, check=False)

    assert syntax.returncode == 0, syntax.stderr
    assert "if ((execution_status == 78)); then" in execution
    assert "unchanged retry is prohibited" in execution


def test_hosted_action_projects_declared_inputs_into_isolated_gate_root() -> None:
    root = Path(__file__).resolve().parents[2]
    action = yaml.safe_load((root / ".github/actions/run-validation-gate/action.yml").read_text(encoding="utf-8"))
    execution = next(step["run"] for step in action["runs"]["steps"] if step.get("id") == "execution")
    catalog_executor = (root / "scripts/validation_control/catalog_execution.py").read_text(encoding="utf-8")

    assert action["outputs"]["output_directory"]["value"] == "${{ steps.gate.outputs.output_directory }}"
    assert 'input_arguments=(--input-directory "$METADATA_DIRECTORY")' in execution
    assert '"${input_arguments[@]}"' in execution
    assert 'environment["WAOOAW_VALIDATION_OUTPUT_DIRECTORY"] = str(artifact_root.resolve())' in catalog_executor


def test_scripts_quality_gate_enforces_execution_contract_self_test() -> None:
    root = Path(__file__).resolve().parents[2]
    catalog = yaml.safe_load((root / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    command_segments = [segment.strip() for segment in catalog["commands"]["quality-scripts"]["shell"].split("&&")]

    assert any(
        segment.startswith("pytest ") and "tests/validation_control/test_unified_execution_contract.py" in segment
        for segment in command_segments
    )


def test_execution_identity_segments_cannot_escape_probe_roots() -> None:
    assert safe_segment("../../gate:name") == "gate-name"


def test_corrupt_failure_record_blocks_costly_retry(tmp_path: Path) -> None:
    path = tmp_path / "test-results/wc106/execution-failures/gate.json"
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")

    with pytest.raises(UnchangedExecutionFailureError, match="unreadable"):
        assert_retry_allowed(tmp_path, "gate", "digest")


def test_orchestration_preflight_rejects_unwritable_home_before_supply(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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


def test_orchestration_preflight_isolates_parallel_output_probes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    socket = tmp_path / "docker.sock"
    socket.touch()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(Path, "is_socket", lambda self: self == socket)
    original_read_text = Path.read_text
    read_barrier = Barrier(2)
    read_paths: list[Path] = []
    read_paths_lock = Lock()

    def synchronized_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path.name.startswith(".orchestration-probe-"):
            with read_paths_lock:
                read_paths.append(path)
            read_barrier.wait()
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", synchronized_read_text)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(orchestration_preflight, tmp_path, socket) for _ in range(2)]
        for future in futures:
            future.result()

    assert len(set(read_paths)) == 2
    assert not list((tmp_path / "test-results/wc106").glob(".orchestration-probe-*"))


def test_all_catalog_runners_use_writable_tmpfs_home() -> None:
    root = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text(encoding="utf-8"))

    for service in ("test-runner-python", "test-runner-dotnet", "test-runner-ts", "test-runner"):
        runner = compose["services"][service]
        assert runner["environment"]["HOME"] == "/tmp"
        assert any(mount.startswith("/tmp:") for mount in runner["tmpfs"])


def test_python_capable_runners_use_bounded_writable_tool_caches() -> None:
    root = Path(__file__).resolve().parents[2]
    compose = yaml.safe_load((root / "docker-compose.yml").read_text(encoding="utf-8"))

    for service in ("test-runner-python", "test-runner"):
        runner = compose["services"][service]
        assert runner["environment"]["RUFF_CACHE_DIR"] == "/tmp/ruff_cache"
        assert any(mount.startswith("/tmp:") for mount in runner["tmpfs"])


def test_rollback_launcher_preserves_docker_authority_and_identity_boundaries() -> None:
    root = Path(__file__).resolve().parents[2]
    launcher = (root / "scripts/validation_control/run_wc104_rollback.sh").read_text(encoding="utf-8")

    assert "docker compose" in launcher
    assert "-e GITHUB_TOKEN" in launcher
    assert '"$repository:$repository:ro"' in launcher
    assert '"$git_common_dir:$git_common_dir:ro"' in launcher
    assert "DOCKER_GID=$docker_gid docker compose" in launcher
    assert '"$docker_socket:$docker_socket"' in launcher
    assert "--user root" not in launcher
    assert "GITHUB_TOKEN is required" in launcher
    assert 'export PYTHONPATH="$PWD/scripts"' in launcher
    assert "--output must be repository-relative below test-results" in launcher
    assert launcher.count('--handoff-evidence "$5"') == 2
    assert "--handoff-evidence requires a path" in launcher
    assert launcher.count("--execution-profile rollback") == 2


def test_normal_qualification_launcher_cannot_enter_rollback_mode() -> None:
    root = Path(__file__).resolve().parents[2]
    launcher_path = root / "scripts/validation_control/run_wc104_qualification.sh"
    launcher = launcher_path.read_text(encoding="utf-8")

    assert launcher_path.stat().st_mode & 0o111
    assert launcher.count("--execution-profile qualification") == 2
    assert "--execution-profile rollback" not in launcher
    assert '"$repository:$repository:ro"' in launcher
    assert '"$docker_socket:$docker_socket"' in launcher


def test_resource_capacity_preflight_passes_without_cleanup_when_capacity_is_safe(tmp_path: Path) -> None:
    usage = SimpleNamespace(total=10_000_000_000, used=8_000_000_000, free=2_000_000_000)
    cleanup_calls: list[Path] = []

    record = resource_capacity_preflight(
        tmp_path,
        [{"resources": {"disk_mb": 1024}}],
        "wc109-capacity-safe",
        disk_usage=lambda path: usage,
        cleanup=lambda path: cleanup_calls.append(path) or [],
    )

    assert record["result"] == "PASS"
    assert record["cleanup_actions"] == []
    assert cleanup_calls == []


def test_resource_capacity_preflight_cleans_once_then_rechecks(tmp_path: Path) -> None:
    usages = iter(
        (
            SimpleNamespace(total=10_000_000_000, used=9_600_000_000, free=400_000_000),
            SimpleNamespace(total=10_000_000_000, used=8_000_000_000, free=2_000_000_000),
        )
    )

    record = resource_capacity_preflight(
        tmp_path,
        [{"resources": {"disk_mb": 1024}}],
        "wc109-capacity-recovered",
        disk_usage=lambda path: next(usages),
        cleanup=lambda path: ["builder prune:0", "image prune:0"],
    )

    assert record["result"] == "PASS"
    assert record["before"]["free_ratio"] < 0.05
    assert record["after"]["free_ratio"] >= 0.05
    assert record["cleanup_actions"] == ["builder prune:0", "image prune:0"]


def test_resource_capacity_preflight_publishes_block_when_cleanup_is_insufficient(tmp_path: Path) -> None:
    usages = iter(
        (
            SimpleNamespace(total=10_000_000_000, used=9_600_000_000, free=400_000_000),
            SimpleNamespace(total=10_000_000_000, used=9_550_000_000, free=450_000_000),
        )
    )

    with pytest.raises(ValueError, match="capacity remains below"):
        resource_capacity_preflight(
            tmp_path,
            [{"resources": {"disk_mb": 1024}}],
            "wc109-capacity-blocked",
            disk_usage=lambda path: next(usages),
            cleanup=lambda path: ["builder prune:0"],
        )

    evidence = tmp_path / "test-results/wc109/runs/wc109-capacity-blocked/resource-preflight.json"
    assert json.loads(evidence.read_text(encoding="utf-8"))["result"] == "BLOCKED"


def test_disposable_cleanup_never_targets_running_or_foreign_projects() -> None:
    commands = disposable_cleanup_commands(
        [
            {"Name": "wc109-stale", "Status": "exited(2)"},
            {"Name": "wc109-active", "Status": "running(3)"},
            {"Name": "customer-stack", "Status": "exited(1)"},
        ],
        "/usr/bin/docker",
    )

    rendered = [" ".join(command) for command in commands]
    assert any("--project-name wc109-stale down" in command for command in rendered)
    assert all("wc109-active" not in command and "customer-stack" not in command for command in rendered)
    assert rendered[-2:] == [
        "/usr/bin/docker builder prune --force --filter until=24h",
        "/usr/bin/docker image prune --force",
    ]

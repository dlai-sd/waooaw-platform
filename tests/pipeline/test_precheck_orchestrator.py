import json
import sys
import time
from pathlib import Path

import pytest

import precheck_orchestrator
from precheck_orchestrator import PrecheckNode, run_prechecks


def python_node(name: str, source: str, *, dependencies: tuple[str, ...] = (), retries: int = 0) -> PrecheckNode:
    return PrecheckNode(
        name=name,
        command=(sys.executable, "-c", source),
        heavy=True,
        dependencies=dependencies,
        transient_retries=retries,
    )


def run(nodes: list[PrecheckNode], artifact_dir: Path, **options: object) -> dict[str, object]:
    return run_prechecks(
        nodes,
        base_sha="b" * 40,
        head_sha="h" * 40,
        changed_file_digest="d" * 64,
        graph_version="test-v1",
        artifact_dir=artifact_dir,
        **options,
    )


def test_independent_gates_run_concurrently(tmp_path: Path) -> None:
    nodes = [
        python_node("one", "import time; time.sleep(0.25)"),
        python_node("two", "import time; time.sleep(0.25)"),
    ]

    started = time.monotonic()
    parallel = run(nodes, tmp_path / "parallel", preflight=lambda: (True, []))
    parallel_elapsed = time.monotonic() - started
    started = time.monotonic()
    serial = run(nodes, tmp_path / "serial", force_serial=True, preflight=lambda: (True, []))
    serial_elapsed = time.monotonic() - started

    assert parallel["mode"] == "parallel"
    assert serial["mode"] == "serial"
    assert parallel_elapsed < serial_elapsed * 0.8
    assert [node["name"] for node in parallel["nodes"]] == [node["name"] for node in serial["nodes"]]
    assert [node["status"] for node in parallel["nodes"]] == ["PASS", "PASS"]


def test_manifest_binds_inputs_and_node_results(tmp_path: Path) -> None:
    manifest = run([python_node("gate", "print('ok')")], tmp_path, preflight=lambda: (True, []))

    assert manifest["schema"] == "waooaw.pr-prechecks/v2"
    assert manifest["base_sha"] == "b" * 40
    assert manifest["commit_sha"] == "h" * 40
    assert manifest["changed_file_digest"] == "d" * 64
    assert manifest["graph_version"] == "test-v1"
    assert manifest["passed"] is True
    assert manifest["nodes"][0]["stdout_artifact"].endswith("gate.stdout.log")


def test_parallel_nodes_have_isolated_namespaces(tmp_path: Path) -> None:
    source = "import json, os; print(json.dumps({k: os.environ[k] for k in ('TMPDIR','COVERAGE_FILE','COMPOSE_PROJECT_NAME')}))"

    run(
        [python_node("one", source), python_node("two", source)],
        tmp_path,
        preflight=lambda: (True, []),
    )
    environments = [json.loads((tmp_path / f"{name}.stdout.log").read_text()) for name in ("one", "two")]

    assert all(len({environment[key] for environment in environments}) == 2 for key in environments[0])


def test_resource_fallback_and_failure_semantics(tmp_path: Path) -> None:
    manifest = run(
        [
            python_node("assertion", "import sys; print('assertion failed', file=sys.stderr); sys.exit(1)"),
            python_node("coverage", "import sys; print('coverage below threshold', file=sys.stderr); sys.exit(1)"),
        ],
        tmp_path,
        preflight=lambda: (False, ["low_memory"]),
    )

    assert manifest["mode"] == "serial"
    assert manifest["fallback_reasons"] == ["low_memory"]
    assert manifest["passed"] is False
    assert [node["classification"] for node in manifest["nodes"]] == ["assertion", "coverage"]
    assert manifest["first_causal_failure"] == "assertion"


def test_dependency_is_not_started_after_prerequisite_failure(tmp_path: Path) -> None:
    marker = tmp_path / "dependent-ran"
    manifest = run(
        [
            python_node("first", "import sys; sys.exit(1)"),
            python_node("dependent", f"from pathlib import Path; Path({str(marker)!r}).touch()", dependencies=("first",)),
        ],
        tmp_path / "artifacts",
        preflight=lambda: (True, []),
    )

    assert manifest["nodes"][1]["status"] == "SKIPPED_DEPENDENCY"
    assert not marker.exists()


def test_cancellation_cannot_produce_passing_aggregate(tmp_path: Path) -> None:
    manifest = run([python_node("cancelled", "import sys; sys.exit(130)")], tmp_path, preflight=lambda: (True, []))

    assert manifest["passed"] is False
    assert manifest["nodes"][0]["classification"] == "cancelled"


def test_interrupt_terminates_workers_and_cleans_compose(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    terminated: list[str] = []
    cleaned: list[str] = []

    class InterruptingFuture:
        def result(self) -> object:
            raise KeyboardInterrupt

    class InterruptingExecutor:
        def __init__(self, **unused: object) -> None:
            pass

        def submit(self, function: object, *arguments: object) -> InterruptingFuture:
            return InterruptingFuture()

        def shutdown(self, *, wait: bool, cancel_futures: bool = False) -> None:
            assert wait is True
            assert cancel_futures is True

    monkeypatch.setattr(precheck_orchestrator, "ThreadPoolExecutor", InterruptingExecutor)
    monkeypatch.setattr(precheck_orchestrator, "_BlockedInterrupts", precheck_orchestrator._NullContext)
    monkeypatch.setattr(precheck_orchestrator, "_terminate_active_processes", lambda: terminated.append("workers"))
    monkeypatch.setattr(
        precheck_orchestrator,
        "_cleanup_compose_projects",
        lambda nodes: cleaned.extend(node.name for node in nodes),
    )

    with pytest.raises(KeyboardInterrupt):
        run(
            [python_node("one", "pass"), python_node("two", "pass")],
            tmp_path,
            preflight=lambda: (True, []),
        )

    assert terminated == ["workers"]
    assert cleaned == ["one", "two"]


def test_long_running_node_emits_progress_signal(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WC100_PROGRESS_INTERVAL_SECONDS", "0.02")

    manifest = run(
        [python_node("slow-gate", "import time; time.sleep(0.06)")],
        tmp_path,
        preflight=lambda: (True, []),
    )

    assert manifest["passed"] is True
    assert "WC-100 precheck still running: slow-gate" in capsys.readouterr().err


def test_transient_infrastructure_retry_is_bounded(tmp_path: Path) -> None:
    marker = tmp_path / "attempted"
    source = (
        "import pathlib, sys; marker=pathlib.Path(" + repr(str(marker)) + "); "
        "exists=marker.exists(); marker.touch(); "
        "print('docker daemon unavailable', file=sys.stderr) if not exists else None; sys.exit(0 if exists else 1)"
    )
    manifest = run([python_node("transient", source, retries=1)], tmp_path / "artifacts", preflight=lambda: (True, []))

    assert manifest["passed"] is True
    assert manifest["nodes"][0]["attempts"] == 2


def test_rollback_and_injected_triggers(tmp_path: Path) -> None:
    manifest = run(
        [python_node("gate", "print('ok')")],
        tmp_path,
        force_serial=True,
        disable_reuse=True,
        preflight=lambda: (True, []),
    )

    assert manifest["mode"] == "serial"
    assert manifest["reuse_enabled"] is False

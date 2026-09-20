import json
from dataclasses import replace
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
        head_sha="a" * 40,
        changed_file_digest="d" * 64,
        graph_version="test-v1",
        configuration_digest="c" * 64,
        runner_digest="r" * 64,
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
    node = replace(
        python_node("gate", "print('ok')"),
        catalog_version="catalog-v1",
        gate_id="test:gate",
        command_id="test-gate",
        gate_implementation_digest="i" * 64,
        runner_digest="sha256:" + "r" * 64,
        environment_digest="e" * 64,
    )
    manifest = run([node], tmp_path, preflight=lambda: (True, []))

    assert manifest["schema"] == "waooaw.pr-prechecks/v4"
    assert manifest["base_sha"] == "b" * 40
    assert manifest["commit_sha"] == "a" * 40
    assert manifest["changed_file_digest"] == "d" * 64
    assert manifest["graph_version"] == "test-v1"
    assert manifest["configuration_digest"] == "c" * 64
    assert manifest["runner_digest"] == "r" * 64
    assert manifest["passed"] is True
    assert manifest["executed_count"] == 1
    assert manifest["reused_count"] == 0
    assert manifest["nodes"][0]["stdout_artifact"].endswith("gate.stdout.log")
    assert manifest["nodes"][0]["authority"] == {
        "catalog_version": "catalog-v1",
        "gate_id": "test:gate",
        "command_id": "test-gate",
        "gate_implementation_digest": "i" * 64,
        "runner_digest": "sha256:" + "r" * 64,
        "environment_digest": "e" * 64,
        "input_digest": "",
        "selector_version": "wc104-gate-inputs-v2",
        "evidence_schema": "waooaw.pr-prechecks/v4",
    }
    assert manifest["nodes"][0]["reuse"]["provenance"] == "executed"


def test_identical_second_run_automatically_reuses_exact_node_evidence(tmp_path: Path) -> None:
    marker = tmp_path / "executions"
    node = python_node(
        "gate",
        f"from pathlib import Path; p=Path({str(marker)!r}); p.write_text(p.read_text() + 'x' if p.exists() else 'x')",
    )

    first = run([node], tmp_path / "artifacts", preflight=lambda: (True, []))
    second = run([node], tmp_path / "artifacts", preflight=lambda: (True, []))

    assert first["executed_count"] == 1
    assert second["executed_count"] == 0
    assert second["reused_count"] == 1
    assert second["nodes"][0]["reuse"]["provenance"] == "exact-candidate"
    assert second["nodes"][0]["reuse"]["trust_source"] == "local-exact-candidate"
    assert marker.read_text() == "x"


def test_changed_node_or_corrupt_artifact_invalidates_only_affected_evidence(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    first = python_node("first", "print('first')")
    second = python_node("second", "print('second')")
    run([first, second], artifact_dir, preflight=lambda: (True, []))

    changed = python_node("second", "print('changed')")
    manifest = run([first, changed], artifact_dir, preflight=lambda: (True, []))
    assert [node["reuse"]["reused"] for node in manifest["nodes"]] == [True, False]

    (artifact_dir / "first.stdout.log").write_text("corrupt", encoding="utf-8")
    manifest = run([first, changed], artifact_dir, preflight=lambda: (True, []))
    assert [node["reuse"]["reused"] for node in manifest["nodes"]] == [False, True]


def test_unaffected_success_is_carried_forward_with_current_head_proof(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    current_dir = tmp_path / "current"
    marker = tmp_path / "executions"
    node = replace(
        python_node(
            "gate",
            f"from pathlib import Path; p=Path({str(marker)!r}); p.write_text(p.read_text() + 'x' if p.exists() else 'x')",
        ),
        input_digest="i" * 64,
        input_patterns=("src/business-platform/**",),
    )
    run([node], source_dir, preflight=lambda: (True, []))

    manifest = run_prechecks(
        [node],
        base_sha="b" * 40,
        head_sha="c" * 40,
        changed_file_digest="e" * 64,
        graph_version="test-v1",
        configuration_digest="c" * 64,
        runner_digest="r" * 64,
        artifact_dir=current_dir,
        reuse_evidence_paths=[source_dir / "precheck-manifest.json"],
        carry_forward_verifier=lambda source, current, patterns: (True, ["reviews/R-144.md"], 1),
        preflight=lambda: (True, []),
    )

    carry = manifest["nodes"][0]["reuse"]["carry_forward"]
    assert manifest["executed_count"] == 0
    assert manifest["commit_sha"] == "c" * 40
    assert carry["source_execution_head"] == "a" * 40
    assert carry["current_head_sha"] == "c" * 40
    assert carry["non_intersection_proven"] is True
    assert manifest["nodes"][0]["reuse"]["provenance"] == "carry-forward"
    assert marker.read_text() == "x"


def test_candidate_arguments_do_not_invalidate_unchanged_gate_command(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source = replace(
        python_node("gate", "print('source')"),
        command=(sys.executable, "-c", "print('source')", "--head", "a" * 40, "--base", "b" * 40),
        input_digest="i" * 64,
        input_patterns=("src/**",),
    )
    run([source], source_dir, preflight=lambda: (True, []))
    current = replace(source, command=(*source.command[:-3], "c" * 40, "--base", "b" * 40))

    manifest = run_prechecks(
        [current],
        base_sha="b" * 40,
        head_sha="c" * 40,
        changed_file_digest="e" * 64,
        graph_version="test-v1",
        configuration_digest="c" * 64,
        runner_digest="r" * 64,
        artifact_dir=tmp_path / "current",
        reuse_evidence_paths=[source_dir / "precheck-manifest.json"],
        carry_forward_verifier=lambda source_head, current_head, patterns: (True, ["reviews/R-144.md"], 1),
        preflight=lambda: (True, []),
    )

    assert manifest["executed_count"] == 0


def test_affected_or_changed_input_cannot_be_carried_forward(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    node = replace(
        python_node("gate", "print('source')"),
        input_digest="i" * 64,
        input_patterns=("src/**",),
    )
    run([node], source_dir, preflight=lambda: (True, []))

    for suffix, candidate, verifier in (
        ("affected", node, lambda source, current, patterns: (False, ["src/changed.py"], 1)),
        ("digest", replace(node, input_digest="j" * 64), lambda source, current, patterns: (True, [], 1)),
    ):
        manifest = run_prechecks(
            [candidate],
            base_sha="b" * 40,
            head_sha="c" * 40,
            changed_file_digest="e" * 64,
            graph_version="test-v1",
            configuration_digest="c" * 64,
            runner_digest="r" * 64,
            artifact_dir=tmp_path / suffix,
            reuse_evidence_paths=[source_dir / "precheck-manifest.json"],
            carry_forward_verifier=verifier,
            preflight=lambda: (True, []),
        )
        assert manifest["executed_count"] == 1
        assert manifest["reused_count"] == 0


def test_malformed_source_manifest_cannot_be_carried_forward(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "precheck-manifest.json").write_text('{"schema":"untrusted","passed":true}', encoding="utf-8")
    node = replace(
        python_node("gate", "print('current')"),
        input_digest="i" * 64,
        input_patterns=("src/**",),
    )

    manifest = run_prechecks(
        [node],
        base_sha="b" * 40,
        head_sha="c" * 40,
        changed_file_digest="e" * 64,
        graph_version="test-v1",
        configuration_digest="c" * 64,
        runner_digest="r" * 64,
        artifact_dir=tmp_path / "current",
        reuse_evidence_paths=[source_dir / "precheck-manifest.json"],
        carry_forward_verifier=lambda source, current, patterns: (True, [], 1),
        preflight=lambda: (True, []),
    )

    assert manifest["executed_count"] == 1
    assert manifest["reused_count"] == 0


def test_nearest_valid_ancestor_is_selected_independent_of_path_order(tmp_path: Path) -> None:
    node = replace(python_node("gate", "print('source')"), input_digest="i" * 64, input_patterns=("src/**",))
    sources = [("far", "1" * 40), ("near", "2" * 40)]
    paths = []
    for directory_name, source_head in sources:
        source_dir = tmp_path / directory_name
        run([node], source_dir, preflight=lambda: (True, []))
        path = source_dir / "precheck-manifest.json"
        evidence = json.loads(path.read_text())
        evidence["commit_sha"] = source_head
        path.write_text(json.dumps(evidence))
        paths.append(path)

    distances = {"1" * 40: 3, "2" * 40: 1}
    manifest = run_prechecks(
        [node],
        base_sha="b" * 40,
        head_sha="c" * 40,
        changed_file_digest="e" * 64,
        graph_version="test-v1",
        configuration_digest="c" * 64,
        runner_digest="r" * 64,
        artifact_dir=tmp_path / "current",
        reuse_evidence_paths=paths,
        carry_forward_verifier=lambda source, current, patterns: (True, [], distances[source]),
        preflight=lambda: (True, []),
    )

    assert manifest["nodes"][0]["reuse"]["carry_forward"]["source_execution_head"] == "2" * 40


def test_invalid_nearest_ancestor_falls_through_to_next_valid(tmp_path: Path) -> None:
    node = replace(python_node("gate", "print('source')"), input_digest="i" * 64, input_patterns=("src/**",))
    paths = []
    for directory_name, source_head in (("far", "1" * 40), ("near", "2" * 40)):
        source_dir = tmp_path / directory_name
        run([node], source_dir, preflight=lambda: (True, []))
        path = source_dir / "precheck-manifest.json"
        evidence = json.loads(path.read_text())
        evidence["commit_sha"] = source_head
        path.write_text(json.dumps(evidence))
        paths.append(path)
    (tmp_path / "near" / "gate.stdout.log").write_text("corrupt")

    distances = {"1" * 40: 3, "2" * 40: 1}
    manifest = run_prechecks(
        [node],
        base_sha="b" * 40,
        head_sha="c" * 40,
        changed_file_digest="e" * 64,
        graph_version="test-v1",
        configuration_digest="c" * 64,
        runner_digest="r" * 64,
        artifact_dir=tmp_path / "current",
        reuse_evidence_paths=reversed(paths),
        carry_forward_verifier=lambda source, current, patterns: (True, [], distances[source]),
        preflight=lambda: (True, []),
    )

    assert manifest["nodes"][0]["reuse"]["carry_forward"]["source_execution_head"] == "1" * 40


@pytest.mark.parametrize("verification", [(False, [], None), (True, [], None)])
def test_unproven_ancestor_or_distance_reruns_node(tmp_path: Path, verification: tuple[bool, list[str], int | None]) -> None:
    source_dir = tmp_path / "source"
    node = replace(python_node("gate", "print('source')"), input_digest="i" * 64, input_patterns=("src/**",))
    run([node], source_dir, preflight=lambda: (True, []))

    manifest = run_prechecks(
        [node],
        base_sha="b" * 40,
        head_sha="c" * 40,
        changed_file_digest="e" * 64,
        graph_version="test-v1",
        configuration_digest="c" * 64,
        runner_digest="r" * 64,
        artifact_dir=tmp_path / "current",
        reuse_evidence_paths=[source_dir / "precheck-manifest.json"],
        carry_forward_verifier=lambda source, current, patterns: verification,
        preflight=lambda: (True, []),
    )

    assert manifest["executed_count"] == 1
    assert manifest["reused_count"] == 0


@pytest.mark.parametrize(
    ("field", "initial", "changed"),
    (
        ("catalog_version", "v1", "v2"),
        ("gate_id", "test:first", "test:first-v2"),
        ("command_id", "command-first", "command-first-v2"),
        ("gate_implementation_digest", "i" * 64, "j" * 64),
        ("runner_digest", "sha256:" + "a" * 64, "sha256:" + "c" * 64),
        ("environment_digest", "b" * 64, "d" * 64),
    ),
)
def test_each_authority_change_invalidates_only_affected_evidence(
    tmp_path: Path,
    field: str,
    initial: str,
    changed: str,
) -> None:
    artifact_dir = tmp_path / "artifacts"
    first = replace(python_node("first", "print('first')"), **{field: initial})
    second = python_node("second", "print('second')")
    run([first, second], artifact_dir, preflight=lambda: (True, []))

    changed_first = replace(first, **{field: changed})
    manifest = run([changed_first, second], artifact_dir, preflight=lambda: (True, []))
    assert [node["reuse"]["reused"] for node in manifest["nodes"]] == [False, True]


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

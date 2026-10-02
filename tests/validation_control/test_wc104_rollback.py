from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

from validation_control.evidence_controller import BLOCKED_DEFERRED_AMENDMENT, BLOCKED_DEFERRED_GATES
from validation_control.orchestrator import build_execution_plan, plan_execution_order, suppression_reason
from validation_control.wc104_rollback import QualificationContext, execute_rollback


HEAD_SHA = "c" * 40
BASE_SHA = "b" * 40


def qualification_context() -> QualificationContext:
    return QualificationContext(
        changed_files=("scripts/example.py",),
        pr_body="## Required Traceability\n",
        base_branch="main",
        pr_number="481",
        repository_name="dlai-sd/waooaw-platform",
    )


def load_catalog() -> dict[str, object]:
    return yaml.safe_load(Path("validation/engineering-validation.yaml").read_text(encoding="utf-8"))


def resolve_services(repository: Path, node: dict[str, object]) -> dict[str, str]:
    return {str(service): "sha256:" + "d" * 64 for service in node["required_services"]}


def execution_ready(repository: Path) -> None:
    assert repository.is_dir()


def resources_ready(repository: Path, nodes: list[dict[str, object]], namespace: str) -> dict[str, object]:
    assert repository.is_dir()
    assert nodes
    assert namespace
    return {"result": "PASS"}


def test_rollback_clean_builds_each_runner_once_then_executes_full_inventory(tmp_path: Path) -> None:
    catalog = load_catalog()
    events: list[tuple[str, str]] = []

    def resolve(repository: Path, runner_id: str) -> dict[str, object]:
        assert os.environ["DOCKER_CONFIG"] == f"/tmp/wc104-docker-{HEAD_SHA}"
        assert Path(os.environ["DOCKER_CONFIG"]).is_dir()
        assert os.environ["WC104_DISABLE_REGISTRY_REUSE"] == "1"
        assert os.environ["WC104_FORCE_LOCAL_BUILD"] == "1"
        events.append(("runner", runner_id))
        return {"build_count": 1, "trust_source": "local-identity-build", "runner_id": runner_id}

    def execute(repository: Path, gate_id: str, head_sha: str, base_sha: str, git_common_dir: Path, **context: object) -> int:
        assert os.environ["WC104_DISABLE_REGISTRY_REUSE"] == "1"
        assert os.environ["WC104_FORCE_LOCAL_BUILD"] == "0"
        assert os.environ["WC100_DISABLE_REUSE"] == "1"
        assert os.environ["WC100_PRECHECK_MODE"] == "serial"
        assert context["changed_files"] == ["scripts/example.py"]
        assert Path(str(context["pr_body_file"])).read_text(encoding="utf-8") == "## Required Traceability\n"
        assert context["base_branch"] == "main"
        assert context["pr_number"] == "481"
        assert context["repository_name"] == "dlai-sd/waooaw-platform"
        events.append(("gate", gate_id))
        return 0

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=resolve,
        service_resolver=resolve_services,
        gate_executor=execute,
    )

    executable_gates = [gate for gate in catalog["full_gates"] if gate not in BLOCKED_DEFERRED_GATES]
    plan = build_execution_plan(catalog, catalog["full_gates"], mode="qualification", head_sha=HEAD_SHA, run_id="clean")
    ordered_gates = plan_execution_order(plan)
    assert events == [("runner", runner) for runner in catalog["runners"]] + [
        ("gate", gate) for gate in ordered_gates if gate not in BLOCKED_DEFERRED_GATES
    ]
    assert result["passed"] is True
    assert [item["gate_id"] for item in result["gate_results"]] == ordered_gates
    deferred = [item for item in result["gate_results"] if item["gate_id"] in BLOCKED_DEFERRED_GATES]
    assert all(item["result"] == "BLOCKED" and item["disposition"] == "BLOCKED-DEFERRED" for item in deferred)
    assert all(
        item["disposition_proof"] == {"founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT, "release_blocking": True}
        for item in deferred
    )
    assert result["first_cause_gate"] is None
    assert [transition["phase"] for transition in result["phase_transitions"]] == [
        "A_DESIGN",
        "B_COMPONENT",
        "C_DEPENDENCY_INTEGRATION",
        "D_SYSTEM_STITCHING",
        "E_QUALIFICATION_HANDOFF",
    ]
    assert all(transition["result"] == "PASS" for transition in result["phase_transitions"])
    assert all(
        item["head_sha"] == HEAD_SHA and item["catalog_digest"] == result["catalog_digest"] for item in result["gate_results"]
    )
    assert result["execution_summary"] == {
        "executed_gate_count": len(executable_gates),
        "resumed_gate_count": 0,
        "suppressed_gate_count": 0,
        "deferred_gate_count": len(BLOCKED_DEFERRED_GATES),
    }


def completed_repair_context(gate_id: str) -> dict[str, object]:
    original_digest = "sha256:" + "1" * 64
    current_digest = "sha256:" + "2" * 64
    return {
        "failure": {
            "routing_class": "PRODUCT",
            "gate_id": gate_id,
            "first_cause": "modeled deterministic failure",
            "binding_digest": original_digest,
        },
        "current_binding_digest": current_digest,
        "affected_gates": [],
        "focused_evidence": [
            {
                "gate_id": gate_id,
                "result": "PASS",
                "mode": "focused",
                "binding_digest": current_digest,
                "trust_source": "catalog-controlled",
                "evidence_identity": "sha256:" + "3" * 64,
            }
        ],
    }


def test_rollback_failure_suppresses_remaining_executable_inventory(tmp_path: Path) -> None:
    catalog = load_catalog()
    executed: list[str] = []
    plan = build_execution_plan(catalog, catalog["full_gates"], mode="qualification", head_sha=HEAD_SHA, run_id="failure")
    ordered_gates = plan_execution_order(plan)

    def execute(repository: Path, gate: str, head: str, base: str, common: Path, **context: object) -> int:
        executed.append(gate)
        return 9 if gate == catalog["full_gates"][1] else 0

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=execute,
    )

    assert result["passed"] is False
    assert len(result["gate_results"]) == len(catalog["full_gates"])
    assert result["gate_results"][1]["result"] == "FAIL"
    expected_executed = ordered_gates[:2]
    assert executed == expected_executed
    assert result["first_cause_gate"] == catalog["full_gates"][1]
    assert [transition["phase"] for transition in result["phase_transitions"]] == ["A_DESIGN"]
    assert result["execution_summary"]["executed_gate_count"] == len(expected_executed)
    assert result["execution_summary"]["resumed_gate_count"] == 0
    assert result["execution_summary"]["suppressed_gate_count"] == sum(
        gate not in BLOCKED_DEFERRED_GATES for gate in ordered_gates[2:]
    )
    assert all(
        item["result"] == "BLOCKED"
        and item["first_cause_gate"] == catalog["full_gates"][1]
        and item["suppression_reason"]
        in {"DEPENDENT_ON_FIRST_CAUSE", "HIGHER_COST_THAN_FIRST_CAUSE", "NEW_WORK_AFTER_FIRST_CAUSE"}
        for item in result["gate_results"][2:]
        if item.get("disposition") == "SUPPRESSED_AFTER_FAILURE"
    )


def test_rollback_records_gate_exception_and_suppresses_remaining_inventory(tmp_path: Path) -> None:
    catalog = load_catalog()
    executed: list[str] = []
    plan = build_execution_plan(catalog, catalog["full_gates"], mode="qualification", head_sha=HEAD_SHA, run_id="exception")
    ordered_gates = plan_execution_order(plan)

    def execute(repository: Path, gate_id: str, head_sha: str, base_sha: str, git_common_dir: Path, **context: object) -> int:
        executed.append(gate_id)
        if gate_id == catalog["full_gates"][1]:
            raise ValueError("modeled execution defect")
        return 0

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=execute,
    )

    assert executed == ordered_gates[:2]
    assert result["passed"] is False
    assert result["gate_results"][1]["error"] == "ValueError: modeled execution defect"
    assert result["first_cause_gate"] == catalog["full_gates"][1]


def test_rollback_atomically_checkpoints_each_terminal_gate(tmp_path: Path) -> None:
    catalog = load_catalog()
    checkpoint = tmp_path / "rollback.json"

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=lambda repository, gate, head, base, common, **context: 7 if gate == "secrets" else 0,
    )

    retained = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert retained["run_state"] == "FAILED"
    assert retained["first_cause_gate"] == "secrets"
    assert retained["gate_results"] == result["gate_results"]
    assert not list(tmp_path.glob("rollback.json.tmp-*"))


def test_rollback_process_interruption_preserves_completed_chunks(tmp_path: Path) -> None:
    checkpoint = tmp_path / "rollback.json"

    def interrupt(repository: Path, gate: str, head: str, base: str, common: Path, **context: object) -> int:
        if gate == "secrets":
            raise SystemExit(143)
        return 0

    with pytest.raises(SystemExit, match="143"):
        execute_rollback(
            tmp_path,
            load_catalog(),
            candidate_sha=HEAD_SHA,
            base_sha=BASE_SHA,
            git_common_dir=tmp_path,
            qualification_context=qualification_context(),
            checkpoint_path=checkpoint,
            execution_preflight=execution_ready,
            resource_preflight=resources_ready,
            runner_resolver=lambda repository, runner: {
                "build_count": 1,
                "trust_source": "local-identity-build",
                "runner_id": runner,
            },
            service_resolver=resolve_services,
            gate_executor=interrupt,
        )

    retained = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert retained["run_state"] == "IN_PROGRESS"
    assert [item["gate_id"] for item in retained["gate_results"]] == ["build"]
    assert retained["gate_results"][0]["result"] == "PASS"
    assert not list(tmp_path.glob("rollback.json.tmp-*"))


def test_rollback_records_operator_cancellation_and_suppresses_later_work(tmp_path: Path) -> None:
    catalog = load_catalog()
    checkpoint = tmp_path / "rollback.json"
    executed: list[str] = []

    def cancel(repository: Path, gate: str, head: str, base: str, common: Path, **context: object) -> int:
        executed.append(gate)
        if gate == "secrets":
            raise KeyboardInterrupt
        return 0

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=cancel,
    )

    assert executed == ["build", "secrets"]
    assert result["gate_results"][1]["result"] == "BLOCKED"
    assert result["gate_results"][1]["disposition"] == "OPERATOR_CANCELLED"
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["gate_results"] == result["gate_results"]


def test_rollback_records_timeout_as_terminal_evidence(tmp_path: Path) -> None:
    catalog = load_catalog()
    checkpoint = tmp_path / "rollback.json"
    executed: list[str] = []

    def timeout(repository: Path, gate: str, head: str, base: str, common: Path, **context: object) -> int:
        executed.append(gate)
        if gate == "secrets":
            raise subprocess.TimeoutExpired(gate, timeout=30)
        return 0

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=timeout,
    )

    timed_out = next(item for item in result["gate_results"] if item["gate_id"] == "secrets")
    assert executed == ["build", "secrets"]
    assert timed_out["result"] == "BLOCKED"
    assert timed_out["disposition"] == "TIMEOUT"
    assert timed_out["returncode"] == 124
    assert json.loads(checkpoint.read_text(encoding="utf-8")) == result


def test_rollback_service_supply_failure_blocks_before_runner_build(tmp_path: Path) -> None:
    catalog = load_catalog()
    checkpoint = tmp_path / "rollback.json"
    runner_calls: list[str] = []
    gate_calls: list[str] = []

    def fail_postgres(repository: Path, node: dict[str, object]) -> dict[str, str]:
        raise ValueError("required service image is unavailable: postgres")

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: runner_calls.append(runner) or {},
        service_resolver=fail_postgres,
        gate_executor=lambda repository, gate, head, base, common, **context: gate_calls.append(gate) or 0,
    )

    assert runner_calls == []
    assert gate_calls == []
    assert result["run_state"] == "BLOCKED"
    assert result["first_cause_gate"] == "preflight:integration:multi-tenant"
    assert result["execution_summary"] == {
        "executed_gate_count": 0,
        "resumed_gate_count": 0,
        "suppressed_gate_count": len(catalog["full_gates"]) - len(BLOCKED_DEFERRED_GATES),
        "deferred_gate_count": len(BLOCKED_DEFERRED_GATES),
    }
    assert next(item for item in result["gate_results"] if item["gate_id"] == "integration:multi-tenant")["error"] == (
        "ValueError: required service image is unavailable: postgres"
    )
    assert json.loads(checkpoint.read_text(encoding="utf-8"))["run_state"] == "BLOCKED"


def test_rollback_authority_failure_publishes_complete_preflight_block(tmp_path: Path) -> None:
    catalog = load_catalog()
    checkpoint = tmp_path / "rollback.json"

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        checkpoint_path=checkpoint,
        context_resolver=lambda repository, base, head: (_ for _ in ()).throw(
            ValueError("rollback PR head does not match candidate HEAD")
        ),
        runner_resolver=lambda repository, runner: pytest.fail("runner must not resolve"),
        service_resolver=lambda repository, node: pytest.fail("service must not resolve"),
        gate_executor=lambda repository, gate, head, base, common, **context: pytest.fail("gate must not execute"),
    )

    assert result["run_state"] == "BLOCKED"
    assert result["first_cause_gate"] == "preflight:qualification-context"
    assert len(result["gate_results"]) == len(catalog["full_gates"])
    assert result["runner_results"] == {}
    assert result["service_results"] == {}
    assert result["preflight_error"] == "ValueError: rollback PR head does not match candidate HEAD"
    assert result["execution_summary"]["executed_gate_count"] == 0
    assert all(item["disposition"] in {"PREFLIGHT_BLOCKED", "BLOCKED-DEFERRED"} for item in result["gate_results"])
    assert next(item for item in result["gate_results"] if item["gate_id"] == "build")["error"] == (
        "ValueError: rollback PR head does not match candidate HEAD"
    )
    assert sum("error" in item for item in result["gate_results"]) == 1
    assert json.loads(checkpoint.read_text(encoding="utf-8")) == result


def test_rollback_plan_failure_publishes_complete_preflight_block(tmp_path: Path) -> None:
    catalog = deepcopy(load_catalog())
    checkpoint = tmp_path / "rollback.json"
    del catalog["gates"]["build"]["cost_class"]

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        execution_preflight=lambda repository: pytest.fail("execution preflight must not run"),
        resource_preflight=lambda repository, nodes, namespace: pytest.fail("resource preflight must not run"),
        runner_resolver=lambda repository, runner: pytest.fail("runner must not resolve"),
        service_resolver=lambda repository, node: pytest.fail("service must not resolve"),
        gate_executor=lambda repository, gate, head, base, common, **context: pytest.fail("gate must not execute"),
    )

    assert result["run_state"] == "BLOCKED"
    assert result["first_cause_gate"] == "preflight:plan"
    assert result["execution_summary"]["executed_gate_count"] == 0
    assert result["runner_results"] == {}
    assert result["service_results"] == {}
    assert len(result["gate_results"]) == len(catalog["full_gates"])
    assert json.loads(checkpoint.read_text(encoding="utf-8")) == result


def test_rollback_execution_preflight_failure_blocks_before_supply(tmp_path: Path) -> None:
    catalog = load_catalog()
    checkpoint = tmp_path / "rollback.json"

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        execution_preflight=lambda repository: (_ for _ in ()).throw(
            ValueError("execution preflight: host-visible output is not writable")
        ),
        runner_resolver=lambda repository, runner: pytest.fail("runner must not resolve"),
        service_resolver=lambda repository, node: pytest.fail("service must not resolve"),
        gate_executor=lambda repository, gate, head, base, common, **context: pytest.fail("gate must not execute"),
    )

    assert result["run_state"] == "BLOCKED"
    assert result["first_cause_gate"] == "preflight:execution-contract"
    assert result["preflight_error"] == "ValueError: execution preflight: host-visible output is not writable"
    assert result["runner_results"] == {}
    assert result["service_results"] == {}
    assert result["execution_summary"]["executed_gate_count"] == 0
    assert len(result["gate_results"]) == len(catalog["full_gates"])
    assert json.loads(checkpoint.read_text(encoding="utf-8")) == result


def test_rollback_resource_failure_blocks_before_supply(tmp_path: Path) -> None:
    catalog = load_catalog()
    checkpoint = tmp_path / "rollback.json"

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        execution_preflight=execution_ready,
        resource_preflight=lambda repository, nodes, namespace: (_ for _ in ()).throw(
            ValueError("resource preflight: workspace capacity remains below the declared safe bound")
        ),
        runner_resolver=lambda repository, runner: pytest.fail("runner must not resolve"),
        service_resolver=lambda repository, node: pytest.fail("service must not resolve"),
        gate_executor=lambda repository, gate, head, base, common, **context: pytest.fail("gate must not execute"),
    )

    assert result["run_state"] == "BLOCKED"
    assert result["first_cause_gate"] == "preflight:resources"
    assert result["runner_results"] == {}
    assert result["service_results"] == {}
    assert result["execution_summary"]["executed_gate_count"] == 0
    assert json.loads(checkpoint.read_text(encoding="utf-8")) == result


def test_rollback_resume_reuses_only_same_identity_pass_results(tmp_path: Path) -> None:
    catalog = load_catalog()
    checkpoint = tmp_path / "rollback.json"

    failed = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=lambda repository, gate, head, base, common, **context: 9 if gate == "secrets" else 0,
    )
    resumed_calls: list[str] = []

    blocked = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        resume_checkpoint=failed,
        execution_preflight=lambda repository: pytest.fail("execution preflight must not run"),
        resource_preflight=lambda repository, nodes, namespace: pytest.fail("resource preflight must not run"),
        runner_resolver=lambda repository, runner: pytest.fail("runner must not resolve"),
        service_resolver=lambda repository, node: pytest.fail("service must not resolve"),
        gate_executor=lambda repository, gate, head, base, common, **context: pytest.fail("gate must not execute"),
    )

    assert blocked["run_state"] == "BLOCKED"
    assert blocked["first_cause_gate"] == "preflight:repair"
    assert blocked["execution_summary"]["executed_gate_count"] == 0

    resumed = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        resume_checkpoint=failed,
        repair_context=completed_repair_context("secrets"),
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=lambda repository, gate, head, base, common, **context: resumed_calls.append(gate) or 0,
    )

    assert "build" not in resumed_calls
    assert resumed_calls[0] == "secrets"
    assert resumed["passed"] is True
    assert resumed["repair_transition"]["restitch_eligible"] is True
    assert resumed["execution_summary"]["resumed_gate_count"] == sum(
        result["result"] == "PASS" for result in failed["gate_results"]
    )
    assert next(item for item in resumed["gate_results"] if item["gate_id"] == "build")["evidence_disposition"] == (
        "same-run-checkpoint"
    )


def test_rollback_failure_retains_independent_reusable_results_only(tmp_path: Path) -> None:
    catalog = load_catalog()
    plan = build_execution_plan(catalog, catalog["full_gates"], mode="qualification", head_sha=HEAD_SHA, run_id="retained")
    ordered_gates = plan_execution_order(plan)
    nodes_by_gate = {node["gate_id"]: node for node in plan["nodes"]}
    failed_gate = next(
        gate_id
        for gate_id in ordered_gates
        if nodes_by_gate[gate_id]["downstream_dependents"] and gate_id not in BLOCKED_DEFERRED_GATES
    )
    dependent_gate = nodes_by_gate[failed_gate]["downstream_dependents"][0]
    independent_gate = next(
        gate_id
        for gate_id in ordered_gates[ordered_gates.index(failed_gate) + 1 :]
        if gate_id not in BLOCKED_DEFERRED_GATES and suppression_reason(plan, gate_id, failed_gate) is None
    )
    completed = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=lambda repository, gate, head, base, common, **context: 0,
    )
    next(item for item in completed["gate_results"] if item["gate_id"] == failed_gate)["result"] = "FAIL"
    executed: list[str] = []

    resumed = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        resume_checkpoint=completed,
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=lambda repository, gate, head, base, common, **context: executed.append(gate) or 9,
    )

    assert executed == [failed_gate]
    assert (
        next(item for item in resumed["gate_results"] if item["gate_id"] == independent_gate)["evidence_disposition"]
        == "same-run-checkpoint"
    )
    assert next(item for item in resumed["gate_results"] if item["gate_id"] == dependent_gate)["disposition"] == (
        "PREREQUISITE_EVIDENCE_BLOCKED"
    )


def test_rollback_resume_runs_only_invalidated_dependency_closure(tmp_path: Path) -> None:
    catalog = load_catalog()
    plan = build_execution_plan(catalog, catalog["full_gates"], mode="qualification", head_sha=HEAD_SHA, run_id="invalidate")
    ordered_gates = plan_execution_order(plan)
    nodes_by_gate = {node["gate_id"]: node for node in plan["nodes"]}
    selected_gate = next(
        gate_id
        for gate_id in ordered_gates
        if nodes_by_gate[gate_id]["downstream_dependents"] and gate_id not in BLOCKED_DEFERRED_GATES
    )
    invalidated = {selected_gate}
    pending = [selected_gate]
    while pending:
        for dependent in nodes_by_gate[pending.pop()]["downstream_dependents"]:
            if dependent not in invalidated:
                invalidated.add(dependent)
                pending.append(dependent)
    completed = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=lambda repository, gate, head, base, common, **context: 0,
    )
    executed: list[str] = []

    resumed = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        resume_checkpoint=completed,
        invalidated_gates=(selected_gate,),
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=lambda repository, gate, head, base, common, **context: executed.append(gate) or 0,
    )

    expected = [gate for gate in ordered_gates if gate in invalidated and gate not in BLOCKED_DEFERRED_GATES]
    assert executed == expected
    assert resumed["invalidated_gates"] == [gate for gate in ordered_gates if gate in invalidated]
    assert resumed["execution_summary"]["resumed_gate_count"] == sum(
        gate not in invalidated and gate not in BLOCKED_DEFERRED_GATES for gate in ordered_gates
    )


def test_rollback_unknown_invalidation_blocks_before_costly_work(tmp_path: Path) -> None:
    result = execute_rollback(
        tmp_path,
        load_catalog(),
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        invalidated_gates=("unknown-gate",),
        execution_preflight=lambda repository: pytest.fail("execution preflight must not run"),
        resource_preflight=lambda repository, nodes, namespace: pytest.fail("resource preflight must not run"),
        runner_resolver=lambda repository, runner: pytest.fail("runner must not resolve"),
        service_resolver=lambda repository, node: pytest.fail("service must not resolve"),
        gate_executor=lambda repository, gate, head, base, common, **context: pytest.fail("gate must not execute"),
    )

    assert result["run_state"] == "BLOCKED"
    assert result["first_cause_gate"] == "preflight:invalidation"
    assert result["execution_summary"]["executed_gate_count"] == 0


def test_rollback_resume_rejects_identity_mismatch_before_execution(tmp_path: Path) -> None:
    catalog = load_catalog()
    manifest = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        execution_preflight=execution_ready,
        resource_preflight=resources_ready,
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        service_resolver=resolve_services,
        gate_executor=lambda repository, gate, head, base, common, **context: 0,
    )
    manifest["candidate_sha"] = "d" * 40

    with pytest.raises(ValueError, match="identity does not match"):
        execute_rollback(
            tmp_path,
            catalog,
            candidate_sha=HEAD_SHA,
            base_sha=BASE_SHA,
            git_common_dir=tmp_path,
            qualification_context=qualification_context(),
            resume_checkpoint=manifest,
            runner_resolver=lambda repository, runner: pytest.fail("runner must not resolve"),
            service_resolver=lambda repository, node: pytest.fail("service must not resolve"),
            gate_executor=lambda repository, gate, head, base, common, **context: pytest.fail("gate must not execute"),
        )

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from validation_control.evidence_controller import BLOCKED_DEFERRED_AMENDMENT, BLOCKED_DEFERRED_GATES
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
    assert events == [("runner", runner) for runner in catalog["runners"]] + [("gate", gate) for gate in executable_gates]
    assert result["passed"] is True
    assert [item["gate_id"] for item in result["gate_results"]] == catalog["full_gates"]
    deferred = [item for item in result["gate_results"] if item["gate_id"] in BLOCKED_DEFERRED_GATES]
    assert all(item["result"] == "BLOCKED" and item["disposition"] == "BLOCKED-DEFERRED" for item in deferred)
    assert all(
        item["disposition_proof"] == {"founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT, "release_blocking": True}
        for item in deferred
    )
    assert result["first_cause_gate"] is None
    assert result["execution_summary"] == {
        "executed_gate_count": len(executable_gates),
        "resumed_gate_count": 0,
        "suppressed_gate_count": 0,
        "deferred_gate_count": len(BLOCKED_DEFERRED_GATES),
    }


def test_rollback_failure_suppresses_remaining_executable_inventory(tmp_path: Path) -> None:
    catalog = load_catalog()
    executed: list[str] = []

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
    assert executed == catalog["full_gates"][:2]
    assert result["first_cause_gate"] == catalog["full_gates"][1]
    assert result["execution_summary"]["executed_gate_count"] == 2
    assert result["execution_summary"]["resumed_gate_count"] == 0
    assert result["execution_summary"]["suppressed_gate_count"] == len(catalog["full_gates"]) - 5
    assert all(
        item["result"] == "BLOCKED" and item["first_cause_gate"] == catalog["full_gates"][1]
        for item in result["gate_results"][2:]
        if item["gate_id"] not in BLOCKED_DEFERRED_GATES
    )


def test_rollback_records_gate_exception_and_suppresses_remaining_inventory(tmp_path: Path) -> None:
    catalog = load_catalog()
    executed: list[str] = []

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

    assert executed == catalog["full_gates"][:2]
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

    resumed = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        checkpoint_path=checkpoint,
        resume_checkpoint=failed,
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
    assert resumed["execution_summary"]["resumed_gate_count"] == 1
    assert next(item for item in resumed["gate_results"] if item["gate_id"] == "build")["evidence_disposition"] == (
        "same-run-checkpoint"
    )


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

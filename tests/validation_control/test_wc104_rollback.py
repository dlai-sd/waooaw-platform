from __future__ import annotations

import os
from pathlib import Path

import yaml

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


def test_rollback_clean_builds_each_runner_once_then_executes_full_inventory_serially(tmp_path: Path) -> None:
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
        runner_resolver=resolve,
        gate_executor=execute,
    )

    assert events == [("runner", runner) for runner in catalog["runners"]] + [("gate", gate) for gate in catalog["full_gates"]]
    assert result["passed"] is True
    assert [item["gate_id"] for item in result["gate_results"]] == catalog["full_gates"]


def test_rollback_records_failure_without_reusing_prior_result(tmp_path: Path) -> None:
    catalog = load_catalog()

    result = execute_rollback(
        tmp_path,
        catalog,
        candidate_sha=HEAD_SHA,
        base_sha=BASE_SHA,
        git_common_dir=tmp_path,
        qualification_context=qualification_context(),
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        gate_executor=lambda repository, gate, head, base, common, **context: 9 if gate == catalog["full_gates"][1] else 0,
    )

    assert result["passed"] is False
    assert len(result["gate_results"]) == len(catalog["full_gates"])
    assert result["gate_results"][1]["result"] == "FAIL"


def test_rollback_records_gate_exception_and_continues_inventory(tmp_path: Path) -> None:
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
        runner_resolver=lambda repository, runner: {
            "build_count": 1,
            "trust_source": "local-identity-build",
            "runner_id": runner,
        },
        gate_executor=execute,
    )

    assert executed == catalog["full_gates"]
    assert result["passed"] is False
    assert result["gate_results"][1]["error"] == "ValueError: modeled execution defect"

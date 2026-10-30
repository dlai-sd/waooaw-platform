"""Keycloak replicas that predate the realm import are restarted before application activation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import goal006_keycloak_realm_refresh as refresh
from scripts import verify_google_deployment as google

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/environment-deployment.yaml"
RG = "waooaw-demo-rg"
REVISION = "ca-demo-keycloak--0000026"
EXECUTION = {"properties": {"status": "Succeeded", "endTime": "2026-10-30T06:44:36+00:00"}}


def replica(name: str, created: str, ready: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "properties": {"createdTime": created, "runningState": "Running", "containers": [{"ready": ready}]},
    }


class FakeAz:
    def __init__(self, replica_sequence: list[list[dict[str, Any]]]) -> None:
        self.replica_sequence = replica_sequence
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> Any:
        self.calls.append(args)
        if args[:2] == ["containerapp", "show"]:
            return REVISION
        if args[:3] == ["containerapp", "replica", "list"]:
            return self.replica_sequence.pop(0) if len(self.replica_sequence) > 1 else self.replica_sequence[0]
        if args[:3] == ["containerapp", "revision", "restart"]:
            return None
        raise AssertionError(args)

    @property
    def restarted(self) -> bool:
        return any(call[:3] == ["containerapp", "revision", "restart"] for call in self.calls)


def run(fake: FakeAz, timeout: int = 60) -> dict[str, Any]:
    clock = iter(range(0, 10_000, 10))
    return refresh.refresh(RG, "demo", EXECUTION, fake, timeout, 10, sleep=lambda _: None, monotonic=lambda: next(clock))


def test_replica_started_before_import_is_restarted_until_fresh_and_ready() -> None:
    fake = FakeAz(
        [
            [replica("old", "2026-10-30T01:58:00Z")],
            [replica("old", "2026-10-30T01:58:00Z")],
            [replica("new", "2026-10-30T06:50:00Z", ready=False)],
            [replica("new", "2026-10-30T06:50:00Z")],
        ]
    )
    evidence = run(fake)
    assert fake.restarted
    assert evidence["restarted"] is True
    assert evidence["stale_replicas"] == ["old"]
    assert evidence["replicas"] == ["new"]
    restart = next(call for call in fake.calls if call[:3] == ["containerapp", "revision", "restart"])
    assert restart[restart.index("--revision") + 1] == REVISION


def test_fresh_ready_replicas_are_left_running() -> None:
    fake = FakeAz([[replica("fresh", "2026-10-30T06:45:00Z")]])
    evidence = run(fake)
    assert not fake.restarted
    assert evidence["restarted"] is False


def test_restart_that_never_refreshes_fails_closed() -> None:
    fake = FakeAz([[replica("old", "2026-10-30T01:58:00Z")]])
    with pytest.raises(RuntimeError, match="did not refresh"):
        run(fake, timeout=30)


def test_failed_import_is_rejected_before_any_restart() -> None:
    fake = FakeAz([[replica("old", "2026-10-30T01:58:00Z")]])
    with pytest.raises(ValueError, match="did not succeed"):
        refresh.refresh(RG, "demo", {"properties": {"status": "Failed"}}, fake, 60, 10)
    assert fake.calls == []


@pytest.mark.parametrize(("group", "environment"), [("waooaw-uat-rg", "demo"), (RG, "prod")])
def test_scope_is_restricted_to_same_environment(group: str, environment: str) -> None:
    with pytest.raises(ValueError, match="restricted"):
        refresh.refresh(group, environment, EXECUTION, FakeAz([[]]), 60, 10)


def test_main_writes_evidence_and_reports_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    execution = tmp_path / "execution.json"
    execution.write_text(json.dumps({"properties": {"status": "Failed"}}), encoding="utf-8")
    output = tmp_path / "evidence.json"
    monkeypatch.setattr(refresh, "_run_az", FakeAz([[]]))
    args = ["--resource-group", RG, "--environment", "demo", "--migration-execution", str(execution)]
    assert refresh.main([*args, "--output", str(output)]) == 1
    assert "did not succeed: status=Failed" in capsys.readouterr().err
    assert not output.exists()


def test_workflow_refreshes_keycloak_after_dependency_readiness_and_before_activation() -> None:
    steps = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["terraform"]["steps"]
    names = [step.get("name") for step in steps]
    position = names.index("Refresh Keycloak replicas after realm import")
    assert names.index("Run vendor schema migrations against private PostgreSQL") < position
    assert names.index("Require runtime dependency revisions before application activation") < position
    assert position < names.index("Plan application activation after migration")
    step = steps[position]
    assert step["if"] == "inputs.apply"
    assert "--migration-execution wc124-keycloak-migration-execution.json" in step["run"]


def test_google_verifier_reports_fixed_failure_message(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    def fail(*_: object) -> dict[str, object]:
        raise ValueError("Broker returned HTTP 400")

    monkeypatch.setattr(google, "verify", fail)
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify",
            "--issuer",
            "https://auth/realms/waooaw",
            "--web-url",
            "https://cp",
            "--release-sha",
            "x",
            "--keycloak-revision",
            REVISION,
            "--output",
            str(tmp_path / "out.json"),
        ],
    )
    assert google.main() == 1
    assert "failed: Broker returned HTTP 400" in capsys.readouterr().out


def test_google_verifier_hides_unexpected_exception_details(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    def fail(*_: object) -> dict[str, object]:
        raise OSError("https://example/?code=secret")

    monkeypatch.setattr(google, "verify", fail)
    monkeypatch.setattr(
        "sys.argv",
        [
            "verify",
            "--issuer",
            "https://auth/realms/waooaw",
            "--web-url",
            "https://cp",
            "--release-sha",
            "x",
            "--keycloak-revision",
            REVISION,
            "--output",
            str(tmp_path / "out.json"),
        ],
    )
    assert google.main() == 1
    out = capsys.readouterr().out
    assert "OSError" in out and "secret" not in out

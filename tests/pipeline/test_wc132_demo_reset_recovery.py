"""WC-132 reset safety and supported runtime configuration contracts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from scripts import goal006_demo_reset_recovery as recovery
from goal006_application_lifecycle import RESET_COMPONENTS, execute

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/environment-deployment.yaml"
EXECUTION = {
    "name": recovery.JOB + "-execution",
    "properties": {"status": "Succeeded", "endTime": "2026-10-30T14:00:00Z"},
}
JOB = {
    "name": recovery.JOB,
    "properties": {
        "configuration": {
            "secrets": [
                {
                    "name": "migration-database",
                    "keyVaultUrl": "https://demo.vault.azure.net/secrets/db-keycloak-migration/version",
                },
            ]
        }
    },
}


class Azure:
    def __init__(self, status: str = "Succeeded") -> None:
        self.calls: list[list[str]] = []
        self.status = status

    def __call__(self, args: list[str]):
        self.calls.append(args)
        if args[:3] == ["containerapp", "job", "show"]:
            return JOB
        if args[:3] == ["containerapp", "job", "start"]:
            return {"name": recovery.JOB + "-execution"}
        if args[:4] == ["containerapp", "job", "execution", "list"]:
            return []
        if args[:4] == ["containerapp", "job", "execution", "show"]:
            return {
                "name": args[args.index("--job-execution-name") + 1],
                "properties": {**EXECUTION["properties"], "status": self.status},
            }
        raise AssertionError(args)


@pytest.fixture
def ready(monkeypatch):
    resume = Mock()
    refresh = Mock(return_value={"ready": True})
    monkeypatch.setattr(recovery, "resume_stopped_app", resume)
    monkeypatch.setattr(recovery, "observe_revision", Mock(return_value={"ready": True}))
    monkeypatch.setattr(recovery, "refresh", refresh)
    return resume, refresh


def test_failed_reset_reimports_existing_realm_then_resumes_and_refreshes(ready):
    azure = Azure()
    result = recovery.recover(run_az=azure)
    assert result["status"] == "passed"
    assert any(call[:3] == ["containerapp", "job", "start"] for call in azure.calls)
    assert ready[0].call_count == 2
    ready[0].assert_any_call(recovery.GROUP, "demo", "ca-demo-pgbouncer", azure)
    ready[0].assert_any_call(recovery.GROUP, "demo", recovery.APP, azure)
    ready[1].assert_called_once()
    assert ready[1].call_args.args[2] == EXECUTION


def test_temporal_or_later_failure_reuses_completed_realm_import(ready):
    azure = Azure()
    recovery.recover(run_az=azure, execution=EXECUTION)
    assert any(call[:4] == ["containerapp", "job", "execution", "show"] for call in azure.calls)
    assert not any(call[:3] == ["containerapp", "job", "start"] for call in azure.calls)
    ready[1].assert_called_once()


def test_local_success_evidence_cannot_override_failed_migration(ready):
    with pytest.raises(RuntimeError, match="realm import failed"):
        recovery.recover(run_az=Azure("Failed"), execution=EXECUTION)
    ready[0].assert_not_called()
    ready[1].assert_not_called()


@pytest.mark.parametrize("name", [None, "job-uat-keycloak-migration-execution", recovery.JOB])
def test_completed_evidence_must_identify_a_demo_migration_execution(name, ready):
    evidence = {**EXECUTION, "name": name}
    with pytest.raises(ValueError, match="unexpected migration execution"):
        recovery.recover(run_az=Azure(), execution=evidence)
    ready[0].assert_not_called()


def test_missing_import_completion_time_never_resumes_consumers(ready):
    azure = Azure()

    def missing_time(args):
        if args[:4] == ["containerapp", "job", "execution", "show"]:
            return {"name": EXECUTION["name"], "properties": {"status": "Succeeded"}}
        return azure(args)

    with pytest.raises(ValueError, match="endTime is missing"):
        recovery.recover(run_az=missing_time, execution=EXECUTION)
    ready[0].assert_not_called()
    ready[1].assert_not_called()


@pytest.mark.parametrize("reuse_evidence", [False, True])
def test_provider_execution_identity_mismatch_never_resumes_consumers(reuse_evidence, ready):
    azure = Azure()

    def wrong_execution(args):
        if args[:4] == ["containerapp", "job", "execution", "show"]:
            return {**EXECUTION, "name": recovery.JOB + "-different"}
        return azure(args)

    with pytest.raises(ValueError, match="unexpected migration execution"):
        recovery.recover(run_az=wrong_execution, execution=EXECUTION if reuse_evidence else None)
    ready[0].assert_not_called()
    ready[1].assert_not_called()


@pytest.mark.parametrize("status", ["Failed", "Stopped", "unexpected"])
def test_import_failure_never_resumes_empty_keycloak(status, ready):
    with pytest.raises(RuntimeError, match="realm import failed"):
        recovery.recover(run_az=Azure(status))
    ready[0].assert_not_called()
    ready[1].assert_not_called()


def test_import_timeout_is_bounded_and_preserves_partial_evidence(ready):
    evidence = {}
    with pytest.raises(RuntimeError, match="import timed out"):
        recovery.recover(run_az=Azure("Running"), timeout=0, evidence=evidence)
    assert evidence["status"] == "failed"
    assert evidence["execution"] == recovery.JOB + "-execution"
    ready[0].assert_not_called()


def test_unready_keycloak_is_not_reported_recovered(ready, monkeypatch):
    monkeypatch.setattr(recovery, "observe_revision", lambda group, app, run_az: {"ready": app != recovery.APP})
    with pytest.raises(RuntimeError, match="readiness timed out"):
        recovery.recover(run_az=Azure(), execution=EXECUTION, timeout=0)
    ready[1].assert_not_called()


def test_unready_pooler_blocks_keycloak_resume(ready, monkeypatch):
    monkeypatch.setattr(recovery, "observe_revision", Mock(return_value={"ready": False}))
    with pytest.raises(RuntimeError, match="PgBouncer readiness timed out"):
        recovery.recover(run_az=Azure(), execution=EXECUTION, timeout=0)
    ready[0].assert_called_once()
    ready[1].assert_not_called()


def test_interrupted_import_is_awaited_without_a_concurrent_import(ready):
    azure = Azure()

    def active_import(args):
        if args[:4] == ["containerapp", "job", "execution", "list"]:
            return [{"name": recovery.JOB + "-existing", "properties": {"status": "Running"}}]
        return azure(args)

    assert recovery.recover(run_az=active_import)["status"] == "passed"
    assert not any(call[:3] == ["containerapp", "job", "start"] for call in azure.calls)


@pytest.mark.parametrize("job", [{"name": "wrong"}, {"name": recovery.JOB, "properties": {"configuration": {"secrets": []}}}])
def test_recovery_preflight_rejects_unbound_job(job):
    with pytest.raises(ValueError):
        recovery.validate_job(job)


def test_main_keeps_named_failure_and_json_evidence(monkeypatch, tmp_path, capsys):
    def fail(**kwargs):
        kwargs["evidence"]["execution"] = "retained"
        raise RuntimeError("realm import failed")

    monkeypatch.setattr(recovery, "recover", fail)
    output = tmp_path / "recovery.json"
    assert (
        recovery.main(
            [
                "--environment",
                "demo",
                "--migration-execution",
                str(tmp_path / "absent.json"),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert "DEMO_KEYCLOAK_REALM_RECOVERY_FAILED" in capsys.readouterr().err
    assert json.loads(output.read_text())["execution"] == "retained"


def test_interrupted_evidence_capture_does_not_prevent_recovery(monkeypatch, tmp_path, capsys):
    imported = tmp_path / "import.json"
    imported.write_text('{"properties":')
    called = Mock(side_effect=lambda **kwargs: kwargs["evidence"].update(status="passed"))
    monkeypatch.setattr(recovery, "recover", called)
    assert (
        recovery.main(
            [
                "--environment",
                "demo",
                "--migration-execution",
                str(imported),
                "--output",
                str(tmp_path / "result.json"),
            ]
        )
        == 0
    )
    assert called.call_args.kwargs["execution"] is None
    assert "DEMO_REALM_IMPORT_EVIDENCE_INVALID" in capsys.readouterr().err


def test_demo_reset_scope_closes_idle_backends_but_has_no_databases():
    assert {"web", "business-platform", "keycloak", "temporal"} <= set(RESET_COMPONENTS)
    assert "pgbouncer" in RESET_COMPONENTS
    assert {"auth-redis", "identity-edge"}.isdisjoint(RESET_COMPONENTS)
    calls = []
    with pytest.raises(ValueError):
        execute("uat", "Stop", component="database-reset", run_az=calls.append)
    assert calls == []


def test_reset_failure_hook_runs_even_when_provisioner_log_capture_fails():
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["terraform"]["steps"]
    named = {step.get("name"): step for step in steps}
    quiesce = named["Quiesce Demo consumers before database reset"]
    reset = named["Run WC-124 database provisioner"]
    repair = named["Recover Keycloak after interrupted Demo reset"]
    assert steps.index(quiesce) < steps.index(reset) < steps.index(repair)
    assert "validate_job" in quiesce["run"]
    assert "DEMO_DATABASE_RESET_MAINTENANCE_STARTED" in quiesce["run"]
    assert "--component database-reset" in quiesce["run"]
    assert reset["id"] == "demo-database-reset"
    assert "always()" in repair["if"] and "(failure() || cancelled())" in repair["if"]
    assert "steps.demo-database-reset.outcome" in repair["if"]
    assert '["success","failure","cancelled"]' in repair["if"]
    assert "inputs.environment == 'demo'" in repair["if"]
    assert "--environment demo" in repair["run"]
    assert "DEMO_DATABASE_RESET_MAINTENANCE_ENDED" in named["Record Demo maintenance window outcome"]["run"]
    upload = named["Upload plans and evidence"]
    assert upload["if"] == "always()"
    assert "wc132-demo-reset-recovery.json" in upload["with"]["path"]


def test_demo_managed_pools_are_not_killed_underneath_and_temporal_skips_test_attributes():
    text = (ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
    assert 'name  = "PGBOUNCER_CLIENT_IDLE_TIMEOUT"\n        value = var.environment == "demo" ? "0" : "60"' in text
    assert 'name  = "PGBOUNCER_SERVER_IDLE_TIMEOUT"\n        value = var.environment == "demo" ? "30" : "300"' in text
    assert text.count("export SKIP_ADD_CUSTOM_SEARCH_ATTRIBUTES=true") == 2
    assert 'name  = "KC_DB_POOL_MIN_SIZE"\n        value = "1"' in text


def test_workflow_uses_exact_node24_action_pins_and_bounded_retention():
    workflow = yaml.safe_load(WORKFLOW.read_text())
    pins = {
        "actions/checkout": "fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09",
        "actions/upload-artifact": "b7c566a772e6b6bfb58ed0dc250532a479d7789f",
        "actions/download-artifact": "37930b1c2abaa49bbe596cd826c3c89aef350131",
        "azure/login": "a641126d1b8aa4d1fa005f4f92df94a3a4c4c906",
    }
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            action, _, pin = step.get("uses", "").partition("@")
            if action in pins:
                assert pin == pins[action]
            retention = step.get("with", {}).get("retention-days")
            if retention is not None:
                assert (
                    int(
                        workflow["env"]["EVIDENCE_RETENTION_DAYS"]
                        if isinstance(retention, str) and retention.startswith("${{")
                        else retention
                    )
                    <= 90
                )

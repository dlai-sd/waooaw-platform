"""Demo cost controls preserve serving revisions, evidence and UAT boundaries."""

import copy
from pathlib import Path

import pytest
import yaml

from goal006_demo_revision_cleanup import main, reconcile

ROOT = Path(__file__).resolve().parents[2]
APP = "ca-demo-web"


class Azure:
    def __init__(self):
        self.shown = {
            "properties": {
                "latestRevisionName": f"{APP}--new",
                "latestReadyRevisionName": f"{APP}--new",
                "configuration": {"ingress": {"traffic": [{"latestRevision": True, "weight": 100}]}},
            }
        }
        self.revisions = [
            {"name": f"{APP}--new", "properties": {"active": True, "healthState": "Healthy", "replicas": 1}},
            {"name": f"{APP}--old", "properties": {"active": True, "healthState": "Healthy", "replicas": 1}},
        ]
        self.mutations = []
        self.show_count = 0
        self.change_during_cleanup = False
        self.stuck = False

    def __call__(self, args):
        if args[:2] == ["containerapp", "list"]:
            return [APP, "ca-uat-web"]
        if args[:2] == ["containerapp", "show"]:
            self.show_count += 1
            if self.change_during_cleanup and self.show_count > 1:
                self.shown["properties"]["latestReadyRevisionName"] = "different"
            return copy.deepcopy(self.shown)
        if args[:3] == ["containerapp", "revision", "list"]:
            assert "--all" in args
            return copy.deepcopy(self.revisions)
        name = args[args.index("--revision") + 1]
        revision = next(revision for revision in self.revisions if revision["name"] == name)
        if args[:3] == ["containerapp", "revision", "deactivate"]:
            self.mutations.append(name)
            if not self.stuck:
                revision["properties"].update(active=False, replicas=0)
            return None
        assert args[:3] == ["containerapp", "revision", "show"]
        return copy.deepcopy(revision)


def test_plan_never_mutates_and_apply_retires_only_old_revision():
    azure = Azure()
    plan = reconcile("waooaw-demo-rg", apply=False, run_az=azure)
    assert plan["plans"][0]["obsolete"] == [f"{APP}--old"]
    assert azure.mutations == []
    result = reconcile("waooaw-demo-rg", apply=True, run_az=azure)
    assert result["status"] == "passed"
    assert azure.mutations == [f"{APP}--old"]
    assert azure.revisions[0]["properties"]["active"] is True
    assert reconcile("waooaw-demo-rg", apply=True, run_az=azure)["retired"] == []


@pytest.mark.parametrize(
    "traffic",
    [
        [{"latestRevision": True, "weight": 90}, {"revisionName": f"{APP}--old", "weight": 10}],
        [{"latestRevision": True, "weight": 100}, {"revisionName": f"{APP}--old", "weight": 0, "label": "rollback"}],
        [],
    ],
)
def test_refuses_split_or_labelled_or_unknown_traffic(traffic):
    azure = Azure()
    azure.shown["properties"]["configuration"]["ingress"]["traffic"] = traffic
    with pytest.raises(ValueError, match="traffic"):
        reconcile("waooaw-demo-rg", apply=True, run_az=azure)
    assert azure.mutations == []


@pytest.mark.parametrize("failure", ["not-ready", "unhealthy", "inactive", "old-traffic"])
def test_refuses_unsafe_rollout(failure):
    azure = Azure()
    if failure == "not-ready":
        azure.shown["properties"]["latestReadyRevisionName"] = f"{APP}--old"
    elif failure == "unhealthy":
        azure.revisions[0]["properties"]["healthState"] = "Unhealthy"
    elif failure == "inactive":
        azure.revisions[0]["properties"]["active"] = False
    else:
        azure.revisions[1]["properties"]["trafficWeight"] = 20
    with pytest.raises(ValueError):
        reconcile("waooaw-demo-rg", apply=True, run_az=azure)
    assert azure.mutations == []


def test_refuses_rollout_race_and_non_demo_scope():
    azure = Azure()
    azure.change_during_cleanup = True
    with pytest.raises(ValueError):
        reconcile("waooaw-demo-rg", apply=True, run_az=azure)
    assert azure.mutations == []
    with pytest.raises(ValueError, match="only"):
        reconcile("waooaw-uat-rg", apply=True, run_az=azure)


def test_refuses_empty_inventory_and_surfaces_azure_failure():
    with pytest.raises(ValueError, match="No Demo apps"):
        reconcile("waooaw-demo-rg", apply=True, run_az=lambda _: [])

    def denied(_):
        raise RuntimeError("Azure authorization denied")

    with pytest.raises(RuntimeError, match="authorization denied"):
        reconcile("waooaw-demo-rg", apply=True, run_az=denied)


def test_times_out_if_replica_remains_after_deactivation():
    azure = Azure()
    azure.stuck = True
    with pytest.raises(RuntimeError, match="zero replicas"):
        reconcile("waooaw-demo-rg", apply=True, run_az=azure, timeout_seconds=0)


def test_cli_records_failure(tmp_path, monkeypatch):
    output = tmp_path / "evidence.json"
    monkeypatch.setattr("sys.argv", ["cleanup", "--resource-group", "waooaw-uat-rg", "--output", str(output)])
    assert main() == 1
    assert '"status": "failed"' in output.read_text()


def test_cleanup_is_after_readiness_and_evidence_is_retained():
    workflow = yaml.safe_load((ROOT / ".github/workflows/environment-deployment.yaml").read_text())
    steps = next(
        job["steps"]
        for job in workflow["jobs"].values()
        if any(step.get("name") == "Retire obsolete Demo revisions after healthy activation" for step in job.get("steps", []))
    )
    names = [step.get("name") for step in steps]
    ready = names.index("Require every activated Container Apps revision to become ready")
    cleanup = names.index("Retire obsolete Demo revisions after healthy activation")
    assert ready < cleanup < names.index("Measure PostgreSQL connection budget after activation")
    assert steps[cleanup]["if"] == "inputs.apply && inputs.environment == 'demo'"
    assert "--apply" in steps[cleanup]["run"]
    assert "demo-revision-cleanup.json" in next(
        step["with"]["path"] for step in steps if "wc124-activation-readiness.json" in step.get("with", {}).get("path", "")
    )


def test_probe_log_suppression_is_demo_only_and_not_global():
    module = (ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text()
    block = module.split("# Successful probe requests dominated Demo ingestion;", 1)[1].split("startup_probe", 1)[0]
    assert 'var.environment == "demo"' in block
    assert '["business-platform", "constitutional-engine"]' in block
    assert '"Logging__LogLevel__Microsoft.AspNetCore.Hosting.Diagnostics"' in block
    assert '"Logging__LogLevel__Microsoft.AspNetCore.Routing.EndpointMiddleware"' in block
    assert "Logging__LogLevel__Default" not in block

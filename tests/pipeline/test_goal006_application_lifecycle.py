import copy
import json
from pathlib import Path

import pytest
import yaml

from goal006_application_lifecycle import START_ORDER, execute, main

ROOT = Path(__file__).resolve().parents[2]


class Azure:
    def __init__(self, environment="demo", state="Running"):
        self.environment = environment
        self.apps = {}
        self.calls = []
        self.mutations = []
        self.stuck = False
        self.fail_at = None
        self.drift = False
        for member in START_ORDER:
            if environment == "uat" and member == "temporal":
                continue
            name = f"ca-{environment}-{member}"
            self.apps[name] = {
                "name": name,
                "properties": {
                    "runningStatus": state,
                    "provisioningState": "Succeeded",
                    "template": {"scale": {"minReplicas": 1}},
                    "configuration": {"ingress": {"traffic": [{"latestRevision": True, "weight": 100}]}},
                },
            }

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["containerapp", "list"]:
            return copy.deepcopy(list(self.apps.values()))
        if args[0] == "rest":
            url = args[args.index("--url") + 1]
            assert "api-version=2025-01-01" in url
            name, operation = url.split("/containerApps/")[1].split("/")
            action = operation.split("?")[0]
            if name == self.fail_at:
                raise RuntimeError("Azure operation denied")
            self.mutations.append((name, action))
            if not self.stuck:
                self.apps[name]["properties"]["runningStatus"] = "Running" if action == "start" else "Stopped"
            if self.drift:
                self.apps[name]["properties"]["template"]["scale"]["minReplicas"] = 2
            return None
        name = args[args.index("-n") + 1] if "-n" in args else args[args.index("--name") + 1]
        app = self.apps[name]
        if args[:2] == ["containerapp", "show"]:
            if "--query" in args:
                return {"latest": name + "--current", "ready": name + "--current"}
            return copy.deepcopy(app)
        properties = {
            "active": True,
            "replicas": 0 if app["properties"]["runningStatus"] == "Stopped" else 1,
            "runningState": "Running",
            "healthState": "Healthy",
        }
        if args[:3] == ["containerapp", "revision", "list"]:
            assert "--all" in args
            return [{"name": name + "--current", "properties": properties}]
        assert args[:3] == ["containerapp", "revision", "show"]
        return {"running": "Running", "health": "Healthy", "replicas": 1, "active": True}


@pytest.mark.parametrize("environment", ["demo"])
def test_complete_stop_start_and_idempotent_replays_preserve_configuration(environment):
    azure = Azure(environment)
    original = {name: copy.deepcopy(app["properties"]["template"]) for name, app in azure.apps.items()}
    stopped = execute(environment, "Stop", run_az=azure)
    assert stopped["status"] == "passed"
    expected = [f"ca-{environment}-{member}" for member in START_ORDER if environment != "uat" or member != "temporal"]
    assert azure.mutations == [(name, "stop") for name in reversed(expected)]
    execute(environment, "Stop", run_az=azure)
    assert len(azure.mutations) == len(expected)
    assert execute(environment, "Start", run_az=azure)["status"] == "passed"
    assert azure.mutations[len(expected) :] == [(name, "start") for name in expected]
    execute(environment, "Start", run_az=azure)
    assert len(azure.mutations) == 2 * len(expected)
    assert original == {name: app["properties"]["template"] for name, app in azure.apps.items()}
    assert all(call[0] in {"containerapp", "rest"} for call in azure.calls)
    assert all("postgres" not in str(call) and "update" not in call and "delete" not in call for call in azure.calls)


@pytest.mark.parametrize("environment,action", [("prod", "Stop"), ("demo", "delete"), ("other", "Start"), ("uat", "Stop")])
def test_rejects_bad_scope_before_provider_access(environment, action):
    azure = Azure()
    with pytest.raises(ValueError):
        execute(environment, action, run_az=azure)
    assert azure.calls == []


@pytest.mark.parametrize("case", ["missing", "extra", "transition"])
def test_inventory_validated_before_any_mutation(case):
    azure = Azure()
    if case == "missing":
        del azure.apps["ca-demo-web"]
    elif case == "extra":
        azure.apps["unowned"] = {"name": "unowned"}
    else:
        azure.apps["ca-demo-web"]["properties"]["runningStatus"] = "Progressing"
    with pytest.raises(ValueError):
        execute("demo", "Stop", run_az=azure)
    assert azure.mutations == []


def test_stop_timeout_records_partial_attempt_and_does_not_continue():
    azure = Azure()
    azure.stuck = True
    evidence = {}
    with pytest.raises(RuntimeError, match="timed out"):
        execute("demo", "Stop", run_az=azure, timeout=0, evidence=evidence)
    assert len(azure.mutations) == 1
    assert evidence["status"] == "failed"
    assert evidence["apps"][0]["status"] == "pending"


def test_failed_operation_can_resume_by_rerunning_same_action():
    azure = Azure()
    azure.fail_at = "ca-demo-dma"
    with pytest.raises(RuntimeError, match="denied"):
        execute("demo", "Stop", run_az=azure)
    assert azure.apps["ca-demo-web"]["properties"]["runningStatus"] == "Stopped"
    azure.fail_at = None
    assert execute("demo", "Stop", run_az=azure)["status"] == "passed"
    assert azure.mutations.count(("ca-demo-web", "stop")) == 1


def test_configuration_drift_fails_without_continuing():
    azure = Azure()
    azure.drift = True
    with pytest.raises(ValueError, match="identity"):
        execute("demo", "Stop", run_az=azure)
    assert len(azure.mutations) == 1


def test_embedded_database_blocks_all_mutations():
    azure = Azure()
    azure.apps["ca-demo-business-platform"]["properties"]["template"]["containers"] = [
        {"name": "postgres", "image": "postgres:16"}
    ]
    with pytest.raises(ValueError, match="database exclusion"):
        execute("demo", "Stop", run_az=azure)
    assert azure.mutations == []


@pytest.mark.parametrize("action", ["Start", "Stop"])
def test_target_running_status_alone_is_not_success(action):
    azure = Azure(state="Stopped" if action == "Start" else "Running")

    def unverified(args):
        response = azure(args)
        if action == "Start" and args[:3] == ["containerapp", "revision", "show"]:
            response["health"] = "Unhealthy"
        if action == "Stop" and args[:3] == ["containerapp", "revision", "list"]:
            for revision in response:
                revision["properties"]["replicas"] = 1
        return response

    with pytest.raises(RuntimeError, match="timed out"):
        execute("demo", action, run_az=unverified, timeout=0)
    assert len(azure.mutations) == 1


def test_cli_persists_provider_failure(tmp_path, monkeypatch):
    output = tmp_path / "operation.json"
    monkeypatch.setattr("sys.argv", ["lifecycle", "--environment", "demo", "--action", "Stop", "--output", str(output)])

    def fail(*args, **kwargs):
        kwargs["evidence"].update(apps=[], status="failed")
        raise RuntimeError("provider denied")

    monkeypatch.setattr("goal006_application_lifecycle.execute", fail)
    assert main() == 1
    assert json.loads(output.read_text())["error"] == "provider denied"


def test_workflow_has_two_inputs_schedule_environment_lock_and_no_deploy_path():
    workflow = yaml.safe_load((ROOT / ".github/workflows/application-lifecycle.yaml").read_text())
    trigger = workflow.get("on", workflow.get(True))
    assert set(trigger["workflow_dispatch"]["inputs"]) == {"environment", "action"}
    assert trigger["workflow_dispatch"]["inputs"]["environment"]["options"] == ["demo"]
    assert trigger["workflow_dispatch"]["inputs"]["action"]["options"] == ["Stop", "Start"]
    assert trigger["schedule"] == [{"cron": "30 16 * * *"}]
    job = workflow["jobs"]["lifecycle"]
    deployment = yaml.safe_load((ROOT / ".github/workflows/deploy.yaml").read_text())
    assert (
        job["concurrency"]["group"].replace("matrix.environment", "inputs.environment || 'demo'")
        == deployment["concurrency"]["group"]
    )
    assert job["concurrency"]["cancel-in-progress"] is False
    assert job["strategy"]["fail-fast"] is False
    assert "'Stop'" in job["env"]["LIFECYCLE_ACTION"]
    source = (ROOT / ".github/workflows/application-lifecycle.yaml").read_text()
    for denied in ("terraform apply", "wc124_azure_lifecycle.py", "flexible-server", "environment-deployment.yaml"):
        assert denied not in source
    assert 'test "$GITHUB_REF" = refs/heads/main' in source
    assert "id-waooaw-$TARGET_ENVIRONMENT-deployment" in source

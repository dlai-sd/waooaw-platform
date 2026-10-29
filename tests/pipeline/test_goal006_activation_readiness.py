"""WC-124 post-activation readiness gate (scripts/goal006_activation_readiness.py)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "goal006_activation_readiness.py"
SPEC = importlib.util.spec_from_file_location("goal006_activation_readiness", SCRIPT)
readiness = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(readiness)


class FakeAzure:
    """Scripted `az` answers; revision states advance per show() call to model convergence."""

    def __init__(self, timeline: dict[str, list[dict]]):
        self.timeline = timeline
        self.calls: dict[str, int] = {app: 0 for app in timeline}

    def __call__(self, args):
        if args[:2] == ["containerapp", "list"]:
            return [*self.timeline, "ca-other-web"]
        # `az containerapp revision show` takes --name <app> --revision <revision>; run 39548319770
        # failed with exit 2 because the script passed a non-existent --app flag.
        assert "--app" not in args
        app = args[args.index("--name") + 1]
        if args[:3] == ["containerapp", "revision", "show"]:
            assert args[args.index("--revision") + 1] == self.timeline[app][min(self.calls[app], len(self.timeline[app]) - 1)]["latest"]
        states = self.timeline[app]
        state = states[min(self.calls[app], len(states) - 1)]
        if args[:2] == ["containerapp", "show"]:
            return {"latest": state["latest"], "ready": state.get("ready"), "status": state.get("status", "Running")}
        self.calls[app] += 1
        return {"running": state["running"], "health": state["health"], "replicas": state.get("replicas", 1),
                "active": state.get("active", True)}


def _clock():
    now = [0.0]

    def clock():
        return now[0]

    def sleep(seconds):
        now[0] += seconds

    return clock, sleep


def test_passes_once_every_latest_revision_is_running_and_healthy():
    azure = FakeAzure({
        "ca-demo-web": [
            {"latest": "ca-demo-web--r2", "ready": "ca-demo-web--r1", "running": "Processing", "health": "None"},
            {"latest": "ca-demo-web--r2", "ready": "ca-demo-web--r2", "running": "Running", "health": "Healthy"},
        ],
        "ca-demo-temporal": [
            {"latest": "ca-demo-temporal--r9", "ready": "ca-demo-temporal--r9", "running": "Running", "health": "Healthy"},
        ],
    })
    clock, sleep = _clock()
    result = readiness.evaluate("rg", "demo", timeout_seconds=120, interval_seconds=15,
                                run_az=azure, clock=clock, sleep=sleep, log=lambda _: None)
    assert result["status"] == "passed"
    assert result["not_ready"] == []
    assert [r["app"] for r in result["revisions"]] == ["ca-demo-temporal", "ca-demo-web"]
    assert result["attempts"] == 2
    # Apps outside the environment prefix are never consulted.
    assert "ca-other-web" not in azure.calls


def test_fails_closed_on_activation_failed_without_waiting_for_the_deadline():
    azure = FakeAzure({
        "ca-demo-billing-engine": [
            {"latest": "ca-demo-billing-engine--r73", "ready": "ca-demo-billing-engine--r67",
             "running": "ActivationFailed", "health": "Unhealthy", "replicas": 0},
        ],
        "ca-demo-web": [
            {"latest": "ca-demo-web--r72", "ready": "ca-demo-web--r72", "running": "Running", "health": "Healthy"},
        ],
    })
    clock, sleep = _clock()
    result = readiness.evaluate("rg", "demo", timeout_seconds=600, interval_seconds=15,
                                run_az=azure, clock=clock, sleep=sleep, log=lambda _: None)
    assert result["status"] == "failed"
    assert result["not_ready"] == ["ca-demo-billing-engine"]
    assert result["attempts"] == 1
    failed = result["revisions"][0]
    assert failed["latest_ready_revision"] == "ca-demo-billing-engine--r67"
    assert "ActivationFailed" in failed["reason"]


def test_scaled_to_zero_apps_are_ready_but_temporal_must_hold_a_replica():
    # Demo runs ce, pr, ai-runtime, billing-engine and dma with min_replicas=0; Azure reports
    # their idle latest revision as ScaledToZero/Healthy, never Running.
    azure = FakeAzure({
        "ca-demo-billing-engine": [
            {"latest": "ca-demo-billing-engine--r74", "ready": "ca-demo-billing-engine--r74",
             "running": "ScaledToZero", "health": "Healthy", "replicas": 0},
        ],
        "ca-demo-temporal": [
            {"latest": "ca-demo-temporal--r9", "ready": "ca-demo-temporal--r9",
             "running": "ScaledToZero", "health": "Healthy", "replicas": 0},
        ],
    })
    clock, sleep = _clock()
    result = readiness.evaluate("rg", "demo", timeout_seconds=30, interval_seconds=15,
                                run_az=azure, clock=clock, sleep=sleep, log=lambda _: None)
    assert result["status"] == "failed"
    assert result["not_ready"] == ["ca-demo-temporal"]
    assert result["revisions"][0]["ready"] is True
    assert "ScaledToZero" in result["revisions"][1]["reason"]


def test_dependency_scope_waits_for_each_dependency_and_a_ready_replica():
    dependency_apps = [
        "ca-demo-auth-redis",
        "ca-demo-identity-edge",
        "ca-demo-keycloak",
        "ca-demo-pgbouncer",
        "ca-demo-temporal",
    ]
    azure = FakeAzure({
        **{
            app: [
                {"latest": f"{app}--r1", "ready": f"{app}--r1", "running": "Running",
                 "health": "Healthy", "replicas": 1},
            ]
            for app in dependency_apps
        },
        "ca-demo-web": [
            {"latest": "ca-demo-web--r1", "ready": "ca-demo-web--r1", "running": "Processing",
             "health": "None", "replicas": 0},
        ],
    })
    clock, sleep = _clock()

    result = readiness.evaluate(
        "rg",
        "demo",
        timeout_seconds=30,
        interval_seconds=15,
        scope="dependencies",
        run_az=azure,
        clock=clock,
        sleep=sleep,
        log=lambda _: None,
    )

    assert result["status"] == "passed"
    assert result["scope"] == "dependencies"
    assert result["not_ready"] == []
    assert [revision["app"] for revision in result["revisions"]] == dependency_apps
    assert azure.calls["ca-demo-web"] == 0


def test_dependency_scope_fails_closed_when_dependency_is_missing_or_scaled_to_zero():
    azure = FakeAzure({
        "ca-demo-pgbouncer": [
            {"latest": "ca-demo-pgbouncer--r1", "ready": "ca-demo-pgbouncer--r1",
             "running": "ScaledToZero", "health": "Healthy", "replicas": 0},
        ],
    })
    clock, sleep = _clock()

    result = readiness.evaluate(
        "rg",
        "demo",
        timeout_seconds=0,
        interval_seconds=15,
        scope="dependencies",
        run_az=azure,
        clock=clock,
        sleep=sleep,
        log=lambda _: None,
    )

    assert result["status"] == "failed"
    assert result["missing_apps"] == [
        "ca-demo-auth-redis",
        "ca-demo-identity-edge",
        "ca-demo-keycloak",
        "ca-demo-temporal",
    ]
    assert result["not_ready"] == sorted([*result["missing_apps"], "ca-demo-pgbouncer"])


def test_stopped_app_is_not_ready_even_when_revision_metadata_is_healthy():
    azure = FakeAzure({
        "ca-demo-pgbouncer": [
            {"latest": "pg--r1", "ready": "pg--r1", "running": "Running", "health": "Healthy",
             "status": "Stopped", "replicas": 1},
        ],
    })
    result = readiness.evaluate("rg", "demo", timeout_seconds=0, interval_seconds=1,
                                scope="migration", run_az=azure, log=lambda _: None)
    assert result["status"] == "failed"
    assert "runningStatus=Stopped" in result["revisions"][0]["reason"]


@pytest.mark.parametrize("scope,members", [
    ("migration", ["pgbouncer"]),
    ("dependencies", ["auth-redis", "identity-edge", "keycloak", "pgbouncer", "temporal"]),
    ("all", ["pgbouncer", "web"]),
])
def test_deployment_resumes_only_selected_stopped_apps_and_is_idempotent(scope, members):
    states = {f"ca-demo-{member}": "Stopped" for member in [*members, "unselected"]}
    starts = []

    def azure(args):
        if args[:2] == ["containerapp", "list"]:
            return list(states)
        if args[0] == "rest":
            url = args[args.index("--url") + 1]
            assert args[1:3] == ["--method", "post"]
            assert url.endswith("/start?api-version=2025-01-01")
            app = url.split("/containerApps/")[1].split("/")[0]
            states[app] = "Running"
            starts.append(app)
            return None
        app = args[args.index("--name") + 1]
        if args[:2] == ["containerapp", "show"]:
            if args[args.index("--query") + 1] == "{id:id,status:properties.runningStatus}":
                return {"id": f"/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/"
                              f"waooaw-demo-rg/providers/Microsoft.App/containerApps/{app}", "status": states[app]}
            return {"latest": app + "--r1", "ready": app + "--r1", "status": states[app]}
        return {"running": "Running", "health": "Healthy", "replicas": 1, "active": True}

    if scope == "all":
        del states["ca-demo-unselected"]
    for _ in range(2):
        result = readiness.evaluate("waooaw-demo-rg", "demo", timeout_seconds=0, interval_seconds=1,
                                    scope=scope, resume_stopped=True, run_az=azure, log=lambda _: None)
        assert result["status"] == "passed"
    assert sorted(starts) == [f"ca-demo-{member}" for member in sorted(members)]
    if scope != "all":
        assert states["ca-demo-unselected"] == "Stopped"


@pytest.mark.parametrize("case", ["wrong-group", "wrong-id", "unknown-state", "denied"])
def test_resume_fails_closed_on_scope_state_or_provider_error(case):
    calls = []

    def azure(args):
        calls.append(args)
        if args[0] == "rest":
            raise RuntimeError("Azure operation denied")
        return {
            "id": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/"
                  f"{'other' if case == 'wrong-id' else 'waooaw-demo-rg'}/providers/Microsoft.App/containerApps/ca-demo-pgbouncer",
            "status": "Unknown" if case == "unknown-state" else "Stopped",
        }

    with pytest.raises((ValueError, RuntimeError)):
        readiness.resume_stopped_app("other" if case == "wrong-group" else "waooaw-demo-rg",
                                      "demo", "ca-demo-pgbouncer", azure)
    assert len([args for args in calls if args[0] == "rest"]) == (1 if case == "denied" else 0)


def test_fails_when_the_bounded_wait_expires_while_still_processing():
    azure = FakeAzure({
        "ca-demo-business-platform": [
            {"latest": "ca-demo-business-platform--r68", "ready": "ca-demo-business-platform--r64",
             "running": "Processing", "health": "None"},
        ],
    })
    clock, sleep = _clock()
    result = readiness.evaluate("rg", "demo", timeout_seconds=45, interval_seconds=15,
                                run_az=azure, clock=clock, sleep=sleep, log=lambda _: None)
    assert result["status"] == "failed"
    assert result["attempts"] == 4
    assert result["not_ready"] == ["ca-demo-business-platform"]


def test_a_running_revision_that_is_not_the_latest_ready_one_is_not_ready():
    # latestReadyRevisionName lagging behind latestRevisionName is exactly the state Terraform
    # apply left behind on Demo; Running alone must not satisfy the gate.
    azure = FakeAzure({
        "ca-demo-web": [
            {"latest": "ca-demo-web--r72", "ready": "ca-demo-web--r68", "running": "Running", "health": "Healthy"},
        ],
    })
    clock, sleep = _clock()
    result = readiness.evaluate("rg", "demo", timeout_seconds=0, interval_seconds=15,
                                run_az=azure, clock=clock, sleep=sleep, log=lambda _: None)
    assert result["status"] == "failed"


@pytest.mark.parametrize("replicas", [0, None, "1"])
def test_running_temporal_without_a_proven_replica_is_not_ready(replicas):
    azure = FakeAzure({
        "ca-demo-temporal": [
            {"latest": "r1", "ready": "r1", "running": "Running", "health": "Healthy", "replicas": replicas},
        ],
    })
    assert readiness.observe_revision("rg", "ca-demo-temporal", azure)["ready"] is False


@pytest.mark.parametrize("active", [None, False, "true"])
def test_missing_or_malformed_active_state_is_not_ready(active):
    azure = FakeAzure({
        "ca-demo-web": [
            {"latest": "r1", "ready": "r1", "running": "Running", "health": "Healthy", "active": active},
        ],
    })
    assert readiness.observe_revision("rg", "ca-demo-web", azure)["ready"] is False


def test_main_writes_evidence_and_returns_nonzero_on_failure(tmp_path, monkeypatch, capsys):
    azure = FakeAzure({
        "ca-demo-web": [
            {"latest": "ca-demo-web--r72", "ready": "ca-demo-web--r68", "running": "ActivationFailed",
             "health": "Unhealthy"},
        ],
    })
    monkeypatch.setattr(readiness, "_run_az", azure)
    output = tmp_path / "wc124-activation-readiness.json"
    rc = readiness.main(["--resource-group", "rg", "--environment", "demo", "--timeout-seconds", "0",
                         "--output", str(output)])
    assert rc == 1
    evidence = json.loads(output.read_text())
    assert evidence["schema"] == readiness.SCHEMA
    assert evidence["status"] == "failed"
    assert "::error::" in capsys.readouterr().err


def test_no_apps_for_environment_is_an_error():
    with pytest.raises(SystemExit):
        readiness.evaluate("rg", "demo", timeout_seconds=0, interval_seconds=1,
                           run_az=lambda args: ["ca-uat-web"], log=lambda _: None)

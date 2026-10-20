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
        app = args[args.index("--name") + 1] if "--app" not in args else args[args.index("--app") + 1]
        states = self.timeline[app]
        state = states[min(self.calls[app], len(states) - 1)]
        if args[:2] == ["containerapp", "show"]:
            return {"latest": state["latest"], "ready": state.get("ready")}
        self.calls[app] += 1
        return {"running": state["running"], "health": state["health"], "replicas": state.get("replicas", 1),
                "active": True}


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

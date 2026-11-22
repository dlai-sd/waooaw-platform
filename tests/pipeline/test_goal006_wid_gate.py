from __future__ import annotations

import json
from typing import Any

import pytest

import goal006_wid_gate as gate

READY_DETAIL = {
    "status": "Healthy",
    "workload_credentials": {
        "credential_source": "keyvault",
        "credential_state": "READY",
        "owner_links": {"billing": "READY", "professional-runtime": "READY"},
    },
}


class FakeAz:
    def __init__(self, statuses: dict[str, list[str]]) -> None:
        self.statuses = statuses
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> Any:
        self.calls.append(args)
        if args[:3] == ["containerapp", "job", "start"]:
            return {"name": f"{args[-1]}-exec"}
        if args[:3] == ["containerapp", "job", "execution"]:
            return self.statuses[args[args.index("--name") + 1]].pop(0)
        return "ca-demo-business-platform.example.io"


def run_gate(az: FakeAz, details: list[dict[str, Any]], **kwargs: int) -> dict[str, Any]:
    queue = list(details)
    return gate.gate(
        "waooaw-demo-rg",
        "demo",
        run=az,
        fetch=lambda _url: queue.pop(0) if len(queue) > 1 else queue[0],
        sleep=lambda _seconds: None,
        **kwargs,
    )


def test_gate_runs_the_ca_job_before_the_leaf_job_and_passes_once_owner_links_are_ready() -> None:
    az = FakeAz({"job-demo-wid-ca-rotator": ["Running", "Succeeded"], "job-demo-wid-leaf-issuer": ["Succeeded"]})

    result = run_gate(az, [{"fetch_error": "URLError"}, READY_DETAIL])

    starts = [call[-1] for call in az.calls if call[:3] == ["containerapp", "job", "start"]]
    assert result["status"] == "passed"
    assert starts == ["job-demo-wid-ca-rotator", "job-demo-wid-leaf-issuer"]
    assert json.dumps(result)


@pytest.mark.parametrize("terminal", ["Failed", "Stopped", "Degraded"])
def test_gate_fails_without_starting_the_leaf_job_when_the_ca_job_does_not_succeed(terminal: str) -> None:
    az = FakeAz({"job-demo-wid-ca-rotator": [terminal]})

    result = run_gate(az, [READY_DETAIL])

    assert result["status"] == "failed"
    assert terminal in result["reason"]
    assert not any("leaf-issuer" in " ".join(call) for call in az.calls)


def test_gate_times_out_a_job_that_never_finishes() -> None:
    az = FakeAz({"job-demo-wid-ca-rotator": ["Running"] * 10})

    result = run_gate(az, [READY_DETAIL], job_timeout_seconds=30, interval_seconds=10)

    assert result["status"] == "failed" and "Running" in result["reason"]


@pytest.mark.parametrize(
    ("credentials", "expected"),
    [
        ({"credential_source": "directory", "credential_state": "READY", "owner_links": {}}, "credential_source"),
        (
            {"credential_source": "keyvault", "credential_state": "UNAVAILABLE", "owner_links": {}},
            "credential_state",
        ),
        (
            {
                "credential_source": "keyvault",
                "credential_state": "READY",
                "owner_links": {"billing": "UNCONFIGURED", "professional-runtime": "READY"},
            },
            "owner_link[billing]=UNCONFIGURED",
        ),
        (
            {
                "credential_source": "keyvault",
                "credential_state": "READY",
                "owner_links": {"billing": "READY"},
            },
            "owner_link[professional-runtime]=MISSING",
        ),
    ],
)
def test_gate_fails_when_business_platform_is_not_using_issued_credentials(credentials: dict[str, Any], expected: str) -> None:
    az = FakeAz({"job-demo-wid-ca-rotator": ["Succeeded"], "job-demo-wid-leaf-issuer": ["Succeeded"]})

    result = run_gate(az, [{"workload_credentials": credentials}], detail_timeout_seconds=20, interval_seconds=10)

    assert result["status"] == "failed" and expected in result["reason"]

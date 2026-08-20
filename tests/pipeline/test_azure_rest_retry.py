"""Tests for bounded Azure REST retries."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.azure_rest_retry import run_azure_rest


def _result(returncode: int, *, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["az", "rest"], returncode, stdout, stderr)


def test_retries_throttle_then_writes_success_atomically(tmp_path: Path, monkeypatch) -> None:
    responses = iter(
        [
            _result(1, stderr='ERROR: Too Many Requests({"error":{"code":"429"}})'),
            _result(0, stdout='{"properties":{"amount":10000}}'),
        ]
    )
    delays: list[float] = []
    monkeypatch.setattr("scripts.azure_rest_retry.subprocess.run", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr("scripts.azure_rest_retry.time.sleep", delays.append)
    output = tmp_path / "response.json"

    assert run_azure_rest("budget", output, ["--method", "get"], base_delay_seconds=2) == 0
    assert output.read_text(encoding="utf-8") == '{"properties":{"amount":10000}}'
    assert delays == [2]
    assert not (tmp_path / "response.json.tmp").exists()


def test_non_transient_failure_does_not_retry_or_leave_output(tmp_path: Path, monkeypatch) -> None:
    calls = 0

    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        return _result(1, stderr="ERROR: AuthorizationFailed")

    monkeypatch.setattr("scripts.azure_rest_retry.subprocess.run", fail)
    output = tmp_path / "response.json"
    output.write_text("stale", encoding="utf-8")

    assert run_azure_rest("actual cost", output, ["--method", "post"]) == 1
    assert calls == 1
    assert not output.exists()


def test_transient_failure_stops_at_attempt_limit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.azure_rest_retry.subprocess.run",
        lambda *args, **kwargs: _result(1, stderr='{"error":{"code":"503"}}'),
    )
    delays: list[float] = []
    monkeypatch.setattr("scripts.azure_rest_retry.time.sleep", delays.append)

    assert run_azure_rest(
        "forecast",
        tmp_path / "response.json",
        ["--method", "post"],
        attempts=3,
        base_delay_seconds=1,
    ) == 1
    assert delays == [1, 2]
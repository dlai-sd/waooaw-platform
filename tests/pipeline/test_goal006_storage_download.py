from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from goal006_storage_download import (  # noqa: E402
    classify_storage_error,
    download_with_retry,
    retry_delay,
)


@pytest.mark.parametrize(
    ("message", "category"),
    (
        ("request may be blocked by network rules", "NETWORK_RULE_NOT_READY"),
        ("AuthorizationFailure", "NETWORK_RULE_NOT_READY"),
        ("BlobNotFound", "BLOB_NOT_FOUND"),
        ("ContainerNotFound", "CONTAINER_NOT_FOUND"),
        ("AuthorizationPermissionMismatch", "AUTHORIZATION_FAILED"),
        ("Too many requests", "THROTTLED"),
        ("unexpected", "UNCLASSIFIED"),
    ),
)
def test_storage_errors_are_classified_without_persisting_messages(message: str, category: str) -> None:
    assert classify_storage_error(message) == category


def test_transient_network_failure_retries_exact_command(tmp_path: Path) -> None:
    results = iter(
        (
            subprocess.CompletedProcess(["az"], 1, "", "network rules"),
            subprocess.CompletedProcess(["az"], 1, "", "network rules"),
            subprocess.CompletedProcess(["az"], 0, "", ""),
        )
    )
    commands: list[Sequence[str]] = []
    delays: list[float] = []

    def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return next(results)

    evidence_path = tmp_path / "attempts.jsonl"
    result = download_with_retry(
        ("az", "storage", "blob", "download"),
        evidence_path=evidence_path,
        attempts=3,
        runner=runner,
        sleeper=delays.append,
    )

    records = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()]
    assert result == 0
    assert len(commands) == 3
    assert delays == [5, 10]
    assert [record["category"] for record in records] == [
        "NETWORK_RULE_NOT_READY",
        "NETWORK_RULE_NOT_READY",
        "SUCCESS",
    ]
    assert all("stderr" not in record for record in records)


def test_exhausted_retry_returns_last_failure_without_secret_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_bearing_error = "network rules token=must-not-be-persisted"

    def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 17, "", secret_bearing_error)

    evidence_path = tmp_path / "attempts.jsonl"
    result = download_with_retry(
        ("az",),
        evidence_path=evidence_path,
        attempts=2,
        runner=runner,
        sleeper=lambda _: None,
    )

    assert result == 17
    assert "must-not-be-persisted" not in evidence_path.read_text(encoding="utf-8")
    assert "must-not-be-persisted" not in capsys.readouterr().err


def test_permanent_storage_failure_does_not_retry(tmp_path: Path) -> None:
    commands: list[Sequence[str]] = []

    def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 1, "", "BlobNotFound")

    evidence_path = tmp_path / "attempts.jsonl"
    result = download_with_retry(
        ("az",),
        evidence_path=evidence_path,
        attempts=12,
        runner=runner,
        sleeper=lambda _: pytest.fail("permanent failure must not sleep"),
    )

    record = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert result == 1
    assert len(commands) == 1
    assert record["category"] == "BLOB_NOT_FOUND"
    assert record["retryable"] is False


def test_retry_delay_is_capped() -> None:
    assert [retry_delay(attempt) for attempt in (1, 2, 3, 4, 5, 20)] == [5, 10, 15, 20, 20, 20]
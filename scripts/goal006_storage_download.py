"""Download a protected GOAL-006 blob after eventual firewall propagation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path


CommandResult = subprocess.CompletedProcess[str]
CommandRunner = Callable[[Sequence[str]], CommandResult]
Sleeper = Callable[[float], None]
RETRYABLE_CATEGORIES = frozenset({"NETWORK_RULE_NOT_READY", "THROTTLED"})


def classify_storage_error(stderr: str) -> str:
    normalized = stderr.lower()
    if "network rules" in normalized or "authorizationfailure" in normalized:
        return "NETWORK_RULE_NOT_READY"
    if "blobnotfound" in normalized:
        return "BLOB_NOT_FOUND"
    if "containernotfound" in normalized:
        return "CONTAINER_NOT_FOUND"
    if "authorizationpermissionmismatch" in normalized or "forbidden" in normalized:
        return "AUTHORIZATION_FAILED"
    if "too many requests" in normalized or "status code: 429" in normalized:
        return "THROTTLED"
    return "UNCLASSIFIED"


def retry_delay(attempt: int) -> int:
    return min(attempt * 5, 20)


def run_command(command: Sequence[str]) -> CommandResult:
    return subprocess.run(command, check=False, capture_output=True, text=True)  # noqa: S603


def download_with_retry(
    command: Sequence[str],
    *,
    evidence_path: Path,
    attempts: int,
    runner: CommandRunner = run_command,
    sleeper: Sleeper = time.sleep,
) -> int:
    if attempts < 1:
        raise ValueError("attempts must be positive")

    started = time.monotonic()
    last_result: CommandResult | None = None
    with evidence_path.open("w", encoding="utf-8") as evidence:
        for attempt in range(1, attempts + 1):
            result = runner(command)
            last_result = result
            category = "SUCCESS" if result.returncode == 0 else classify_storage_error(result.stderr)
            retryable = category in RETRYABLE_CATEGORIES
            delay = retry_delay(attempt) if attempt < attempts and retryable else 0
            record = {
                "attempt": attempt,
                "category": category,
                "delay_before_next_seconds": delay,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "recorded_at": datetime.now(UTC).isoformat(),
                "retryable": retryable,
            }
            evidence.write(json.dumps(record, sort_keys=True) + "\n")
            evidence.flush()
            if result.returncode == 0:
                return 0
            if delay:
                sleeper(delay)
            else:
                break

    assert last_result is not None
    category = classify_storage_error(last_result.stderr)
    print(f"Blob download failed after {attempts} attempts: {category}", file=sys.stderr)
    return last_result.returncode or 1


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--container-name", required=True)
    parser.add_argument("--blob-name", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--attempts", type=positive_integer, default=12)
    arguments = parser.parse_args()
    command = (
        "az",
        "storage",
        "blob",
        "download",
        "--account-name",
        arguments.account_name,
        "--container-name",
        arguments.container_name,
        "--name",
        arguments.blob_name,
        "--file",
        str(arguments.output),
        "--auth-mode",
        "login",
        "--overwrite",
        "--only-show-errors",
        "--output",
        "none",
    )
    return download_with_retry(command, evidence_path=arguments.evidence, attempts=arguments.attempts)


if __name__ == "__main__":
    raise SystemExit(main())
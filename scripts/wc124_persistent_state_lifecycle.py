#!/usr/bin/env python3
"""Build and advance fail-closed WC-124 persistent-state lifecycle records."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §§9.4-11.1
# Constitutional basis: C-023, C-059, C-063, C-066, C-080

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SHA256 = re.compile(r"sha256:[0-9a-f]{64}$")
FULL_SHA = re.compile(r"[0-9a-f]{40}$")
TERMINAL_STATES = {
    "ACTIVE",
    "SLEEPING",
    "FAILED_ACTIVATION",
    "FAILED_SLEEP",
    "RECOVERY_HOLD",
    "SECURITY_HOLD",
}
TRANSITIONS = {
    "SLEEPING": {"ACTIVATING_DATABASE", "RECOVERY_HOLD", "SECURITY_HOLD"},
    "ACTIVATING_DATABASE": {
        "ACTIVATING_GATEWAY",
        "FAILED_ACTIVATION",
        "RECOVERY_HOLD",
        "SECURITY_HOLD",
    },
    "ACTIVATING_GATEWAY": {"MIGRATING", "FAILED_ACTIVATION", "SECURITY_HOLD"},
    "MIGRATING": {
        "ACTIVATING_DEPENDENCIES",
        "FAILED_ACTIVATION",
        "RECOVERY_HOLD",
        "SECURITY_HOLD",
    },
    "ACTIVATING_DEPENDENCIES": {
        "ACTIVATING_APPLICATIONS",
        "FAILED_ACTIVATION",
        "SECURITY_HOLD",
    },
    "ACTIVATING_APPLICATIONS": {"VERIFYING", "FAILED_ACTIVATION", "SECURITY_HOLD"},
    "VERIFYING": {
        "ACTIVE",
        "FAILED_ACTIVATION",
        "RECOVERY_HOLD",
        "SECURITY_HOLD",
    },
    "ACTIVE": {"DRAINING", "RECOVERY_HOLD", "SECURITY_HOLD"},
    "DRAINING": {
        "SLEEPING_DEPENDENCIES",
        "FAILED_SLEEP",
        "RECOVERY_HOLD",
        "SECURITY_HOLD",
    },
    "SLEEPING_DEPENDENCIES": {"STOPPING_DATABASE", "FAILED_SLEEP", "SECURITY_HOLD"},
    "STOPPING_DATABASE": {
        "SLEEPING",
        "FAILED_SLEEP",
        "RECOVERY_HOLD",
        "SECURITY_HOLD",
    },
}
ACTION_STEPS = {
    "activate": [
        "ACTIVATING_DATABASE",
        "ACTIVATING_GATEWAY",
        "MIGRATING",
        "ACTIVATING_DEPENDENCIES",
        "ACTIVATING_APPLICATIONS",
        "VERIFYING",
        "ACTIVE",
    ],
    "sleep": [
        "DRAINING",
        "SLEEPING_DEPENDENCIES",
        "STOPPING_DATABASE",
        "SLEEPING",
    ],
}
AUTHORIZATION_FIELDS = {
    "founder_action_authority",
    "runner_execution_identity",
    "release_sha",
    "plan_digest",
    "secret_catalog_digest",
    "lease_id",
    "lease_expiry",
}


class LifecycleError(RuntimeError):
    """A lifecycle request or record failed closed."""


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def validate_authorization(
    authorization: dict[str, Any],
    *,
    environment: str,
    now: datetime | None = None,
) -> None:
    if set(authorization) != AUTHORIZATION_FIELDS:
        missing = sorted(AUTHORIZATION_FIELDS - set(authorization))
        extra = sorted(set(authorization) - AUTHORIZATION_FIELDS)
        raise LifecycleError(f"authorization tuple mismatch: missing={missing} extra={extra}")
    if not str(authorization["founder_action_authority"]).startswith("FA-"):
        raise LifecycleError("Founder action authority is invalid")
    if authorization["runner_execution_identity"] != f"id-waooaw-{environment}-deployment-writer":
        raise LifecycleError("runner execution identity is not environment-exact")
    if FULL_SHA.fullmatch(str(authorization["release_sha"])) is None:
        raise LifecycleError("release SHA is invalid")
    for field in ("plan_digest", "secret_catalog_digest"):
        if SHA256.fullmatch(str(authorization[field])) is None:
            raise LifecycleError(f"{field} is invalid")
    if not str(authorization["lease_id"]).strip():
        raise LifecycleError("authorization lease ID is invalid")
    try:
        expiry = datetime.fromisoformat(str(authorization["lease_expiry"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise LifecycleError("lease expiry must be RFC3339") from error
    if expiry.tzinfo is None:
        raise LifecycleError("lease expiry must include timezone")
    observed_at = now or datetime.now(timezone.utc)
    if expiry.astimezone(timezone.utc) <= observed_at.astimezone(timezone.utc):
        raise LifecycleError("authorization lease is expired")


def next_steps(action: str, current_state: str) -> list[str]:
    if action == "plan":
        return []
    if action not in ACTION_STEPS:
        raise LifecycleError("action must be plan, activate, or sleep")
    required_start = "SLEEPING" if action == "activate" else "ACTIVE"
    if current_state != required_start:
        raise LifecycleError(f"{action} requires current state {required_start}")
    return list(ACTION_STEPS[action])


def advance_record(
    record: dict[str, Any],
    *,
    target_state: str,
    evidence_digest: str,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    current_state = str(record["state"])
    if target_state not in TRANSITIONS.get(current_state, set()):
        raise LifecycleError(f"transition denied: {current_state} -> {target_state}")
    if SHA256.fullmatch(evidence_digest) is None:
        raise LifecycleError("step evidence digest is invalid")
    prior_digest = canonical_digest(record)
    updated = dict(record)
    updated.update(
        {
            "state": target_state,
            "step_watermark": int(record["step_watermark"]) + 1,
            "previous_record_digest": prior_digest,
            "step_evidence_digest": evidence_digest,
            "updated_at": (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    updated["record_digest"] = canonical_digest({key: value for key, value in updated.items() if key != "record_digest"})
    return updated


def create_record(
    *,
    operation_id: str,
    action: str,
    environment: str,
    current_state: str,
    authorization: dict[str, Any],
    tuple_digests: dict[str, str],
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    if environment not in {"demo", "uat"}:
        raise LifecycleError("persistent-state lifecycle is authorized only for Demo and UAT")
    if not operation_id or len(operation_id) > 128:
        raise LifecycleError("operation ID is invalid")
    validate_authorization(authorization, environment=environment, now=observed_at)
    expected_tuple_fields = {
        "configuration",
        "dependency",
        "migration",
        "release",
        "schema",
    }
    if set(tuple_digests) != expected_tuple_fields or any(SHA256.fullmatch(value) is None for value in tuple_digests.values()):
        raise LifecycleError("release/configuration/dependency/schema/migration tuple is incomplete")
    steps = next_steps(action, current_state)
    timestamp = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    record: dict[str, Any] = {
        "schema": "waooaw.wc124-persistent-state-lifecycle/v1",
        "operation_id": operation_id,
        "requested_action": action,
        "environment": environment,
        "state": current_state,
        "target_state": steps[-1] if steps else current_state,
        "planned_steps": steps,
        "authorization_digest": canonical_digest(authorization),
        "evidence_writer_identity": authorization["runner_execution_identity"],
        "tuple_digests": dict(sorted(tuple_digests.items())),
        "step_watermark": 0,
        "attempt": 1,
        "previous_record_digest": None,
        "step_evidence_digest": None,
        "created_at": timestamp.isoformat().replace("+00:00", "Z"),
        "updated_at": timestamp.isoformat().replace("+00:00", "Z"),
        "hold_reason": None,
        "residual_monthly_cost": None,
        "retained_authoritative_data": True,
    }
    record["record_digest"] = canonical_digest(record)
    return record


def validate_record_chain(
    records: list[dict[str, Any]],
    *,
    environment: str,
    verifier_identity: str,
) -> None:
    if not records:
        raise LifecycleError("lifecycle evidence chain is empty")
    expected_writer = f"id-waooaw-{environment}-deployment-writer"
    expected_verifier = f"id-waooaw-{environment}-independent-verifier"
    if verifier_identity != expected_verifier or verifier_identity == expected_writer:
        raise LifecycleError("lifecycle verifier is not independent and environment-exact")
    previous: dict[str, Any] | None = None
    for index, record in enumerate(records):
        if record.get("environment") != environment:
            raise LifecycleError("lifecycle evidence environment mismatch")
        if record.get("evidence_writer_identity") != expected_writer:
            raise LifecycleError("lifecycle evidence writer mismatch")
        actual_digest = record.get("record_digest")
        expected_digest = canonical_digest({key: value for key, value in record.items() if key != "record_digest"})
        if actual_digest != expected_digest:
            raise LifecycleError("lifecycle evidence digest mismatch")
        expected_previous = None if previous is None else canonical_digest(previous)
        if record.get("previous_record_digest") != expected_previous:
            raise LifecycleError("lifecycle evidence chain is truncated or replaced")
        if record.get("step_watermark") != index:
            raise LifecycleError("lifecycle evidence watermark is not contiguous")
        previous = record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--action", choices=("plan", "activate", "sleep"), required=True)
    parser.add_argument("--environment", choices=("demo", "uat"), required=True)
    parser.add_argument("--current-state", required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--tuple-digests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    record = create_record(
        operation_id=arguments.operation_id,
        action=arguments.action,
        environment=arguments.environment,
        current_state=arguments.current_state,
        authorization=json.loads(arguments.authorization.read_text(encoding="utf-8")),
        tuple_digests=json.loads(arguments.tuple_digests.read_text(encoding="utf-8")),
    )
    arguments.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

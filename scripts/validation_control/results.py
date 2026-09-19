"""Create, validate, and aggregate WC-102 validation result envelopes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import jsonschema


MAX_FIRST_CAUSE = 512
REDACTIONS = (
    re.compile(r"(?i)bearer\s+[^\s]+"),
    re.compile(r"(?i)(?:token|password|secret|authorization)[=:]\s*[^\s]+"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)


def sanitize_first_cause(message: str) -> str:
    sanitized = " ".join(message.split())
    for pattern in REDACTIONS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized[:MAX_FIRST_CAUSE]


def build_result(
    *,
    base_sha: str,
    head_sha: str,
    runner_digest: str,
    component: str,
    gate: str,
    command_id: str,
    started_at: str,
    duration_ms: int,
    exit_code: int,
    result: str,
    failure_class: str,
    first_cause: str,
    raw_artifacts: list[str],
    reuse: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "runner_digest": runner_digest,
        "component": component,
        "gate": gate,
        "command_id": command_id,
        "started_at": started_at,
        "duration_ms": duration_ms,
        "exit_code": exit_code,
        "result": result,
        "failure_class": failure_class,
        "first_cause": sanitize_first_cause(first_cause),
        "raw_artifacts": raw_artifacts,
        "reuse": reuse or {"reused": False, "trust_source": "original-run", "invalidation_reason": "not-reused"},
    }


def aggregate_results(
    results: list[dict[str, Any]],
    required_gates: list[str],
    base_sha: str,
    head_sha: str,
    schema: dict[str, Any] | None,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    if schema is None:
        import json

        schema_path = Path(__file__).resolve().parents[2] / "validation/result.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

    by_gate: dict[str, dict[str, Any]] = {}
    for result in results:
        gate = result.get("gate")
        if not isinstance(gate, str):
            raise ValueError("MALFORMED_RESULT: unknown")
        if gate in by_gate:
            raise ValueError(f"DUPLICATE_RESULT: {gate}")
        try:
            jsonschema.validate(result, schema)
        except jsonschema.ValidationError as error:
            raise ValueError(f"MALFORMED_RESULT: {gate}") from error
        if result["base_sha"] != base_sha or result["head_sha"] != head_sha:
            raise ValueError(f"STALE_RESULT: {gate}")
        if artifact_root is not None:
            for artifact in result["raw_artifacts"]:
                artifact_path = (artifact_root / artifact).resolve()
                if not artifact_path.is_relative_to(artifact_root.resolve()) or not artifact_path.is_file():
                    raise ValueError(f"MISSING_ARTIFACT: {gate}: {artifact}")
        by_gate[gate] = result

    for gate in required_gates:
        if gate not in by_gate:
            raise ValueError(f"MISSING_RESULT: {gate}")

    failures = sorted(
        (
            result
            for gate, result in by_gate.items()
            if gate in required_gates and result["result"] not in {"PASS", "NOT_APPLICABLE"}
        ),
        key=lambda result: result["started_at"],
    )
    first_failure = None
    if failures:
        first_failure = {
            "gate": failures[0]["gate"],
            "failure_class": failures[0]["failure_class"],
            "first_cause": failures[0]["first_cause"],
        }
    return {
        "schema": "waooaw.validation-aggregate/v1",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "result": "FAIL" if failures else "PASS",
        "required_gates": required_gates,
        "first_failure": first_failure,
    }

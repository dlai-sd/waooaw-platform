#!/usr/bin/env python3
"""Fail closed unless current identity and Temporal evidence permit activation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from cli_errors import fail_cli
from wc124_db_provisioner import REQUIRED_IDENTITY_RELATIONS, expected_identity_policy_digest


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"evidence must be a JSON object: {path}")
    return value


def execution_name(execution: dict[str, Any], kind: str) -> str:
    name = execution.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{kind} execution evidence has no execution name")
    if execution.get("properties", {}).get("status") != "Succeeded":
        raise ValueError(f"{kind} execution did not succeed")
    return name


def validate_identity(identity: dict[str, Any], expected_execution: str) -> None:
    if identity.get("execution") != expected_execution:
        raise ValueError("identity evidence is stale or bound to a different execution")
    schema = identity.get("identity_schema")
    if not isinstance(schema, dict) or schema.get("status") != "passed":
        raise ValueError("identity catalog verification did not pass")
    required = schema.get("required_relations")
    if required != list(REQUIRED_IDENTITY_RELATIONS):
        raise ValueError("identity evidence has a missing, extra, or reordered required relation contract")
    relations = schema.get("relations")
    if not isinstance(relations, dict) or set(relations) != set(REQUIRED_IDENTITY_RELATIONS):
        raise ValueError("identity catalog evidence is incomplete")
    for name in REQUIRED_IDENTITY_RELATIONS:
        relation = relations.get(name)
        if not isinstance(relation, dict):
            raise ValueError(f"identity relation evidence is malformed: {name}")
        if not all(relation.get(field) is True for field in ("exists", "rls", "forced_rls", "actor_scope_policy")):
            raise ValueError(f"identity relation failed catalog verification: {name}")
        digest = relation.get("policy_definition_sha256")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"identity policy definition evidence is malformed: {name}")
        if digest != expected_identity_policy_digest(name):
            raise ValueError(f"identity policy definition differs from the trusted contract: {name}")


def validate_temporal(temporal: dict[str, Any], expected_execution: str) -> None:
    if temporal.get("execution") != expected_execution:
        raise ValueError("Temporal evidence is stale or bound to a different execution")
    exact_values = {
        "status": "passed",
        "temporal_pool_size_per_database": 8,
        "sql_max_connections_per_store_per_service": 1,
        "max_waiting_clients": 0,
        "max_wait_seconds": 0,
        "query_wait_timeout_events": 0,
    }
    for field, expected in exact_values.items():
        if temporal.get(field) != expected:
            raise ValueError(f"Temporal evidence failed {field}: expected {expected!r}")
    if not isinstance(temporal.get("qualification_seconds"), int) or temporal["qualification_seconds"] < 60:
        raise ValueError("Temporal qualification window is shorter than 60 seconds")
    if not isinstance(temporal.get("minimum_postgresql_headroom"), int) or temporal["minimum_postgresql_headroom"] < 5:
        raise ValueError("Temporal qualification did not preserve five PostgreSQL connections of headroom")
    observation = temporal.get("observation")
    if not isinstance(observation, dict) or not observation.get("start_time") or not observation.get("end_time"):
        raise ValueError("Temporal observation window evidence is missing")


def validate_evidence(
    *,
    environment: str,
    identity: dict[str, Any],
    identity_execution: dict[str, Any],
    temporal: dict[str, Any] | None,
    temporal_execution: dict[str, Any] | None,
) -> dict[str, Any]:
    identity_name = execution_name(identity_execution, "identity provisioning")
    validate_identity(identity, identity_name)
    temporal_name: str | None = None
    if environment == "demo":
        if temporal is None or temporal_execution is None:
            raise ValueError("Demo activation requires Temporal pool evidence")
        temporal_name = execution_name(temporal_execution, "Temporal qualification")
        validate_temporal(temporal, temporal_name)
    return {
        "schema": "waooaw.wc124-pre-activation-evidence/v1",
        "environment": environment,
        "identity_execution": identity_name,
        "temporal_execution": temporal_name,
        "status": "accepted-for-activation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True, choices=("demo", "uat"))
    parser.add_argument("--identity", required=True, type=Path)
    parser.add_argument("--identity-execution", required=True, type=Path)
    parser.add_argument("--temporal", type=Path)
    parser.add_argument("--temporal-execution", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        result = validate_evidence(
            environment=arguments.environment,
            identity=load_object(arguments.identity),
            identity_execution=load_object(arguments.identity_execution),
            temporal=load_object(arguments.temporal) if arguments.temporal else None,
            temporal_execution=load_object(arguments.temporal_execution) if arguments.temporal_execution else None,
        )
        arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        fail_cli(parser, str(error), cause=error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

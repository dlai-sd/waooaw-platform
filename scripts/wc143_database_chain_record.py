#!/usr/bin/env python3
"""Record and evaluate reuse of an unchanged WC-124 database authority chain (WC-143).

A record is written only after a deployment completed the full chain and succeeded. A later
deployment reuses the recorded evidence only when every input fingerprint and live fact still
matches; any doubt, error or missing record selects the full chain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RECORD_SCHEMA = "waooaw.wc143-database-chain-record/v1"
REUSE_SCHEMA = "waooaw.wc143-database-chain-reuse/v1"
PROVISIONER_RESULT_SCHEMA = "waooaw.wc124-db-provisioning/v1"
AUTHORITY_SCHEMA = "waooaw.wc124-reconciliation-authority/v1"
# The chain rotates nothing, so age only bounds how long an undetected out-of-band change can persist.
MAX_RECORD_AGE = timedelta(days=7)
CLOCK_SKEW = timedelta(minutes=5)
STEADY_STATE = "REVOKED"
CHAIN_INPUTS = (
    "scripts/wc124_db_provisioner.py",
    "scripts/wc124_db_handoff.py",
    "scripts/wc124_database_transition.py",
    "scripts/wc124_pre_activation_evidence.py",
    "scripts/wc143_database_chain_record.py",
    "scripts/cli_errors.py",
    "infrastructure/environment-readiness/secret-catalog.json",
)
INIT_DIRECTORY = "infrastructure/postgres/init"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def chain_fingerprint(
    repository_root: Path,
    environment: str,
    context: Mapping[str, str] | None = None,
    extra_files: tuple[Path, ...] = (),
) -> str:
    if environment not in {"demo", "uat"}:
        raise ValueError("environment must be demo or uat")
    files = [repository_root / name for name in CHAIN_INPUTS]
    files += sorted(path for path in (repository_root / INIT_DIRECTORY).rglob("*") if path.is_file())
    files += sorted(extra_files)
    missing = [str(path) for path in files if not path.is_file()]
    if missing or len(files) <= len(CHAIN_INPUTS):
        raise ValueError(f"database chain inputs are missing: {missing or INIT_DIRECTORY}")
    digest = hashlib.sha256()
    digest.update(f"environment:{environment}\0".encode())
    for name, value in sorted((context or {}).items()):
        digest.update(f"context:{name}\0{value}\0".encode())
    for path in files:
        digest.update(f"file:{path.relative_to(repository_root).as_posix()}\0".encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def seal(body: dict[str, Any]) -> dict[str, Any]:
    return {**body, "record_sha256": hashlib.sha256(canonical(body)).hexdigest()}


def create_record(
    *,
    environment: str,
    fingerprint: str,
    live_facts: dict[str, Any],
    provisioner_result: dict[str, Any],
    provisioner_execution: dict[str, Any],
    run_id: str,
    recorded_at: datetime,
) -> dict[str, Any]:
    return seal(
        {
            "schema": RECORD_SCHEMA,
            "environment": environment,
            "fingerprint": fingerprint,
            "recorded_at": recorded_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": run_id,
            "live_facts": live_facts,
            "provisioner_result": provisioner_result,
            "provisioner_execution": provisioner_execution,
        }
    )


def reject_reason(
    record: dict[str, Any],
    *,
    environment: str,
    fingerprint: str,
    live_facts: dict[str, Any],
    now: datetime,
    reset_requested: bool,
    transition_state: str,
    expected_spend_paise: int | None,
) -> str | None:
    """Return why the record cannot be reused, or None when every binding holds."""
    if reset_requested:
        return "database reset requested"
    if transition_state != STEADY_STATE:
        return f"transition state is {transition_state}, not {STEADY_STATE}"
    if record.get("schema") != RECORD_SCHEMA or record.get("environment") != environment:
        return "record schema or environment does not match"
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    if record.get("record_sha256") != hashlib.sha256(canonical(body)).hexdigest():
        return "record integrity digest does not match"
    if record.get("fingerprint") != fingerprint:
        return "chain input fingerprint changed"
    if canonical(record.get("live_facts")) != canonical(live_facts):
        return "live database or credential facts changed"
    recorded_at = parse_time(str(record.get("recorded_at")))
    if recorded_at - now > CLOCK_SKEW:
        return "record is dated in the future"
    if now - recorded_at > MAX_RECORD_AGE:
        return f"record is older than {MAX_RECORD_AGE.days} days"
    result = record.get("provisioner_result")
    execution = record.get("provisioner_execution")
    if not isinstance(result, dict) or not isinstance(execution, dict):
        return "recorded provisioner evidence is missing"
    if result.get("schema") != PROVISIONER_RESULT_SCHEMA or result.get("mode") == "canonical-url-refresh":
        return "recorded provisioner result is not a full provisioning result"
    if result.get("database_reset") is not None:
        return "recorded provisioner result came from a database reset"
    if not execution.get("name") or result.get("execution") != execution.get("name"):
        return "recorded provisioner evidence is not bound to one execution"
    if execution.get("properties", {}).get("status") != "Succeeded":
        return "recorded provisioner execution did not succeed"
    if result.get("identity_schema", {}).get("status") != "passed":
        return "recorded identity catalog verification did not pass"
    if expected_spend_paise is not None:
        spend = result.get("spend_authority")
        if not isinstance(spend, dict) or spend.get("maximum_paise") != expected_spend_paise:
            return "recorded spend authority differs from the current Founder policy"
    return None


def reuse_evidence(record: dict[str, Any], now: datetime) -> dict[str, dict[str, Any]]:
    """Evidence files the later activation gates read, labelled as reused from the record."""
    recorded_at = parse_time(record["recorded_at"])
    return {
        "wc124-db-provisioner-result.json": record["provisioner_result"],
        "wc124-db-provisioner-execution.json": record["provisioner_execution"],
        "wc124-reconciliation-authority.json": {
            "schema": AUTHORITY_SCHEMA,
            "status": "temporary-authority-revoked",
            "ownership": "not-opened-chain-reused",
            "cleanup": "not-required",
            "reused_chain": True,
            "record_fingerprint": record["fingerprint"],
        },
        "wc143-database-chain-reuse.json": {
            "schema": REUSE_SCHEMA,
            "status": "reused-bound-record",
            "environment": record["environment"],
            "fingerprint": record["fingerprint"],
            "record_sha256": record["record_sha256"],
            "recorded_at": record["recorded_at"],
            "recorded_run_id": record["run_id"],
            "execution": record["provisioner_execution"]["name"],
            "age_seconds": int((now - recorded_at).total_seconds()),
        },
    }


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def parse_context(values: list[str]) -> dict[str, str]:
    context: dict[str, str] = {}
    for value in values:
        name, separator, content = value.partition("=")
        if not separator or not name:
            raise ValueError("context must be name=value")
        context[name] = content
    return context


def command_fingerprint(arguments: argparse.Namespace) -> int:
    print(
        chain_fingerprint(
            arguments.repository_root,
            arguments.environment,
            parse_context(arguments.context),
            tuple(arguments.input_file),
        )
    )
    return 0


def command_create(arguments: argparse.Namespace) -> int:
    record = create_record(
        environment=arguments.environment,
        fingerprint=arguments.fingerprint,
        live_facts=load_object(arguments.live_facts),
        provisioner_result=load_object(arguments.provisioner_result),
        provisioner_execution=load_object(arguments.provisioner_execution),
        run_id=arguments.run_id,
        recorded_at=datetime.now(timezone.utc),
    )
    arguments.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def command_evaluate(arguments: argparse.Namespace) -> int:
    """Always prints a decision; any error or doubt means the full chain runs."""
    decision: dict[str, Any] = {"reuse": False, "reason": "unknown"}
    try:
        if not arguments.record.is_file():
            decision["reason"] = "no record exists"
        else:
            now = datetime.now(timezone.utc)
            record = load_object(arguments.record)
            reason = reject_reason(
                record,
                environment=arguments.environment,
                fingerprint=arguments.fingerprint,
                live_facts=load_object(arguments.live_facts),
                now=now,
                reset_requested=arguments.reset_requested == "true",
                transition_state=str(load_object(arguments.transition).get("state")),
                expected_spend_paise=arguments.expected_spend_paise,
            )
            if reason is None:
                for name, content in reuse_evidence(record, now).items():
                    (arguments.output_directory / name).write_text(
                        json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                    )
                decision = {"reuse": True, "reason": "every binding matches the recorded full chain"}
            else:
                decision["reason"] = reason
    except (OSError, ValueError, KeyError, TypeError) as error:
        decision = {"reuse": False, "reason": f"record could not be evaluated: {type(error).__name__}"}
    print(json.dumps(decision, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    fingerprint = commands.add_parser("fingerprint")
    fingerprint.add_argument("--repository-root", type=Path, default=Path("."))
    fingerprint.add_argument("--environment", required=True)
    fingerprint.add_argument("--context", action="append", default=[])
    fingerprint.add_argument("--input-file", action="append", default=[], type=Path)
    fingerprint.set_defaults(handler=command_fingerprint)

    create = commands.add_parser("create")
    create.add_argument("--environment", required=True)
    create.add_argument("--fingerprint", required=True)
    create.add_argument("--live-facts", required=True, type=Path)
    create.add_argument("--provisioner-result", required=True, type=Path)
    create.add_argument("--provisioner-execution", required=True, type=Path)
    create.add_argument("--run-id", required=True)
    create.add_argument("--output", required=True, type=Path)
    create.set_defaults(handler=command_create)

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--record", required=True, type=Path)
    evaluate.add_argument("--environment", required=True)
    evaluate.add_argument("--fingerprint", required=True)
    evaluate.add_argument("--live-facts", required=True, type=Path)
    evaluate.add_argument("--transition", required=True, type=Path)
    evaluate.add_argument("--reset-requested", required=True, choices=("true", "false"))
    evaluate.add_argument("--expected-spend-paise", type=int)
    evaluate.add_argument("--output-directory", required=True, type=Path)
    evaluate.set_defaults(handler=command_evaluate)

    arguments = parser.parse_args()
    try:
        return arguments.handler(arguments)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

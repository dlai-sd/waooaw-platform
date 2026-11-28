#!/usr/bin/env python3
"""Record, plan and evaluate the WC-124 database authority chain (WC-143, WC-177).

A record is written only after a deployment succeeded. A later deployment chooses one of three
database paths from the repository, the sealed record and the live facts, never from the database:

* ``reuse``  - nothing database-related changed; the recorded chain evidence is reused.
* ``update`` - only new init files, each declared ``-- wc177-apply: update`` and lint-clean, differ;
  the update job applies them and the record is rewritten.
* ``full``   - anything else, including any doubt, error or unreadable record.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import re
import sys
import tarfile
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import wc124_init_chain_lint as init_lint

RECORD_SCHEMA = "waooaw.wc143-database-chain-record/v2"
LEGACY_RECORD_SCHEMA = "waooaw.wc143-database-chain-record/v1"
REUSE_SCHEMA = "waooaw.wc143-database-chain-reuse/v1"
PLAN_SCHEMA = "waooaw.wc177-database-plan/v1"
UPDATE_SCHEMA = "waooaw.wc177-database-update/v1"
PROVISIONER_RESULT_SCHEMA = "waooaw.wc124-db-provisioning/v1"
AUTHORITY_SCHEMA = "waooaw.wc124-reconciliation-authority/v1"
SCHEMA_VERSION = 2
# The chain rotates nothing, so age only bounds how long an undetected out-of-band change can persist.
MAX_RECORD_AGE = timedelta(days=7)
CLOCK_SKEW = timedelta(minutes=5)
STEADY_STATE = "REVOKED"
# The init files are not chain inputs: they are tracked one by one in the record (WC-177).
CHAIN_INPUTS = (
    "scripts/wc124_db_provisioner.py",
    "scripts/wc124_db_handoff.py",
    "scripts/wc124_database_transition.py",
    "scripts/wc124_pre_activation_evidence.py",
    "scripts/wc143_database_chain_record.py",
    "scripts/cli_errors.py",
    "infrastructure/environment-readiness/secret-catalog.json",
    "infrastructure/postgres/init/00-wc124-principal-bootstrap.sql",
)
INIT_DIRECTORY = "infrastructure/postgres/init"
BOOTSTRAP_FILE = "00-wc124-principal-bootstrap.sql"
# Container Apps passes the pending files as one environment variable; stay far below its limit.
MAX_UPDATE_PAYLOAD_BYTES = 90_000
PATHS = ("reuse", "update", "full")
UPDATE_OWNER_ROLES = ("bp_owner", "wbe_owner")
# The vendor migrations and the Temporal qualification depend on these definitions only.
VENDOR_RESOURCES = (
    ("azurerm_container_app", "pgbouncer"),
    ("azurerm_container_app_job", "keycloak_migration"),
    ("azurerm_container_app_job", "temporal_migration"),
    ("azurerm_container_app_job", "temporal_startup_qualification"),
)
VENDOR_WORKFLOW_STEPS = (
    "Run vendor schema migrations against private PostgreSQL",
    "Qualify exact Temporal startup through PgBouncer",
)
VENDOR_FILES = (
    "scripts/wc124_pgbouncer_preflight_job.py",
    "scripts/wait_for_replicas_drained.sh",
)
WORKLOAD_MODULE = "infrastructure/terraform/phase2/modules/workload/main.tf"
DEPLOYMENT_WORKFLOW = ".github/workflows/environment-deployment.yaml"
# The deployed definition of these resources (rendered realm, secret versions, images, arguments) is read
# from the migration plan; repository text alone cannot see Terraform variables such as the Keycloak realm.
VENDOR_ADDRESSES = (
    "module.workload.azurerm_container_app.pgbouncer[0]",
    "module.workload.azurerm_container_app_job.keycloak_migration[0]",
    "module.workload.azurerm_container_app_job.temporal_migration[0]",
    "module.workload.azurerm_container_app_job.temporal_startup_qualification[0]",
)
VENDOR_PLAN_FIELDS = (
    "template",
    "secret",
    "identity",
    "ingress",
    "registry",
    "replica_retry_limit",
    "replica_timeout_in_seconds",
)


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
    files += sorted(extra_files)
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise ValueError(f"database chain inputs are missing: {missing}")
    digest = hashlib.sha256()
    digest.update(f"environment:{environment}\0".encode())
    for name, value in sorted((context or {}).items()):
        digest.update(f"context:{name}\0{value}\0".encode())
    for path in files:
        digest.update(f"file:{path.relative_to(repository_root).as_posix()}\0".encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def init_files(repository_root: Path) -> dict[str, Path]:
    """Every ``*.sql`` init file the provisioner applies, in C-locale order (bootstrap excluded)."""
    directory = repository_root / INIT_DIRECTORY
    if not (directory / BOOTSTRAP_FILE).is_file():
        raise ValueError(f"principal bootstrap file is missing: {BOOTSTRAP_FILE}")
    paths = sorted(
        (path for path in directory.glob("*.sql") if path.name != BOOTSTRAP_FILE),
        key=lambda path: path.name.encode(),
    )
    if not paths:
        raise ValueError(f"init chain has no application files in {INIT_DIRECTORY}")
    return {path.name: path for path in paths}


def init_file_digests(repository_root: Path) -> dict[str, str]:
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in init_files(repository_root).items()}


def file_class(text: str) -> str:
    """``update`` only when the first non-blank line is the update header; anything else is ``full``."""
    return init_lint.declared_class(text)


def classify_files(repository_root: Path, names: list[str]) -> dict[str, dict[str, Any]]:
    """Class, digest and lint findings (idempotent standard plus update rules) for the named files."""
    paths = init_files(repository_root)
    result: dict[str, dict[str, Any]] = {}
    for name in names:
        text = paths[name].read_text(encoding="utf-8")
        declared = file_class(text)
        findings = [f"{item.rule}@{item.line}" for item in init_lint.lint_sql(name, text)]
        if declared == "update":
            findings += [f"{item.rule}@{item.line}" for item in init_lint.update_rule_findings(name, text)]
        result[name] = {
            "class": declared,
            "sha256": hashlib.sha256(paths[name].read_bytes()).hexdigest(),
            "findings": findings,
        }
    return result


def _resource_block(text: str, kind: str, name: str) -> str:
    match = re.search(rf'^resource "{kind}" "{name}" {{\n.*?^}}\n', text, re.M | re.S)
    if not match:
        raise ValueError(f"vendor resource is missing: {kind}.{name}")
    return match.group(0)


def _workflow_step(text: str, name: str) -> str:
    start = text.index(f"      - name: {name}\n")
    following = re.search(r"\n      - (?:name|uses): ", text[start + 1 :])
    return text[start : start + 1 + following.start()] if following else text[start:]


def plan_definition_digest(plan: dict[str, Any]) -> str:
    """Digest of the planned definitions of the vendor resources present in a migration plan."""
    changes = {
        change.get("address"): change
        for change in plan.get("resource_changes", [])
        if isinstance(change, dict) and change.get("address") in VENDOR_ADDRESSES
    }
    if not changes:
        raise ValueError("the migration plan contains none of the vendor resources")
    selected: dict[str, Any] = {}
    for address, change in sorted(changes.items()):
        after = (change.get("change") or {}).get("after")
        if not isinstance(after, dict):
            raise ValueError(f"the migration plan has no planned definition for {address}")
        unknown = (change.get("change") or {}).get("after_unknown") or {}
        selected[address] = {
            "after": {field: after.get(field) for field in VENDOR_PLAN_FIELDS},
            "unknown": {field: unknown.get(field) for field in VENDOR_PLAN_FIELDS},
        }
    return hashlib.sha256(canonical(selected)).hexdigest()


def vendor_qualification_digest(repository_root: Path, plan: dict[str, Any]) -> str:
    """Digest of everything the vendor migrations and Temporal qualification are defined by."""
    module = (repository_root / WORKLOAD_MODULE).read_text(encoding="utf-8")
    workflow = (repository_root / DEPLOYMENT_WORKFLOW).read_text(encoding="utf-8")
    digest = hashlib.sha256()
    for kind, name in VENDOR_RESOURCES:
        digest.update(_resource_block(module, kind, name).encode())
    for step in VENDOR_WORKFLOW_STEPS:
        digest.update(_workflow_step(workflow, step).encode())
    for name in VENDOR_FILES:
        digest.update((repository_root / name).read_bytes())
    digest.update(plan_definition_digest(plan).encode())
    return digest.hexdigest()


def update_payload(repository_root: Path, names: list[str]) -> tuple[str, str]:
    """Deterministic gzip tar of the named files (base64) and its sha256sum-format manifest."""
    paths = init_files(repository_root)
    manifest = "".join(
        f"{hashlib.sha256(paths[name].read_bytes()).hexdigest()}  {name}\n" for name in sorted(names, key=str.encode)
    )
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for name in sorted(names, key=str.encode):
                data = paths[name].read_bytes()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mtime = 0
                info.mode = 0o444
                archive.addfile(info, io.BytesIO(data))
    return base64.b64encode(buffer.getvalue()).decode("ascii"), manifest


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
    applied_init_files: Mapping[str, str] | None = None,
    vendor: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return seal(
        {
            "schema": RECORD_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "environment": environment,
            "fingerprint": fingerprint,
            "recorded_at": recorded_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": run_id,
            "live_facts": live_facts,
            "provisioner_result": provisioner_result,
            "provisioner_execution": provisioner_execution,
            "applied_init_files": dict(applied_init_files or {}),
            "vendor": vendor,
            "checkpoint": checkpoint,
        }
    )


def refresh_record(
    previous: dict[str, Any],
    *,
    run_id: str,
    recorded_at: datetime,
    applied_init_files: Mapping[str, str] | None = None,
    vendor: dict[str, Any] | None = None,
    live_facts: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rewrite a verified record after an update or a vendor qualification; the chain evidence is kept."""
    body = {key: value for key, value in previous.items() if key != "record_sha256"}
    body.update(
        {
            "recorded_at": recorded_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": run_id,
            "previous_record_sha256": previous["record_sha256"],
        }
    )
    if applied_init_files is not None:
        body["applied_init_files"] = dict(applied_init_files)
    if vendor is not None:
        body["vendor"] = vendor
    if live_facts is not None:
        body["live_facts"] = live_facts
    if checkpoint is not None:
        body["checkpoint"] = checkpoint
    return seal(body)


def make_checkpoint(release_sha: str | None, run_id: str) -> dict[str, Any] | None:
    """Stage checkpoint: the database and migration stage groups completed for this release."""
    if not release_sha:
        return None
    return {"release_sha": release_sha, "run_id": run_id, "stage": "database-and-migrations-complete"}


def resume_decision(
    record: dict[str, Any] | None,
    *,
    requested: str,
    release_sha: str | None,
    path: str,
) -> dict[str, Any]:
    """Honour ``resume_from=activation`` only when the checkpoint of this release is intact.

    The checkpoint is written after the database and migration stage groups were verified, and the
    ``reuse`` path plus the vendor plan (digest equality) then skip those groups; anything else starts
    from the beginning.
    """
    if requested != "activation":
        return {"requested": requested, "honoured": False, "reason": "resume was not requested"}
    checkpoint = record.get("checkpoint") if isinstance(record, dict) else None
    if path != "reuse":
        reason = "the database stage group is not intact; the deployment starts from the beginning"
    elif not isinstance(checkpoint, dict) or not release_sha or checkpoint.get("release_sha") != release_sha:
        reason = "the checkpoint is missing or bound to a different release; the deployment starts from the beginning"
    else:
        return {"requested": requested, "honoured": True, "reason": "database and migration checkpoint is intact"}
    return {"requested": requested, "honoured": False, "reason": reason}


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
    if record.get("schema") == LEGACY_RECORD_SCHEMA:
        return "record is version 1; one full chain replaces it with a version 2 record"
    if record.get("schema") != RECORD_SCHEMA or record.get("environment") != environment:
        return "record schema or environment does not match"
    body = {key: value for key, value in record.items() if key != "record_sha256"}
    if record.get("record_sha256") != hashlib.sha256(canonical(body)).hexdigest():
        return "record integrity digest does not match"
    if record.get("fingerprint") != fingerprint:
        return "chain input fingerprint changed"
    applied = record.get("applied_init_files")
    if (
        not isinstance(applied, dict)
        or not applied
        or not all(
            isinstance(name, str) and isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
            for name, value in applied.items()
        )
    ):
        return "record does not list the applied init files"
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


def reuse_evidence(record: dict[str, Any], now: datetime, path: str = "reuse") -> dict[str, dict[str, Any]]:
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
            "database_path": path,
            "environment": record["environment"],
            "fingerprint": record["fingerprint"],
            "record_sha256": record["record_sha256"],
            "recorded_at": record["recorded_at"],
            "recorded_run_id": record["run_id"],
            "execution": record["provisioner_execution"]["name"],
            "age_seconds": int((now - recorded_at).total_seconds()),
        },
    }


def vendor_reuse_evidence(record: dict[str, Any], current_digest: str | None, path: str) -> dict[str, Any] | None:
    """Recorded vendor evidence, only when the chain is skipped and every vendor input is unchanged."""
    vendor = record.get("vendor")
    if path not in {"reuse", "update"} or current_digest is None or not isinstance(vendor, dict):
        return None
    if vendor.get("digest") != current_digest:
        return None
    migrations = vendor.get("migrations")
    temporal = vendor.get("temporal_pool")
    execution = vendor.get("temporal_execution")
    executions = migrations.get("executions") if isinstance(migrations, dict) else None
    if (
        not isinstance(executions, list)
        or not executions
        or not all(isinstance(item, dict) and item.get("status") == "Succeeded" for item in executions)
    ):
        return None
    if (temporal is None) != (execution is None) or (record.get("environment") == "demo" and temporal is None):
        return None
    if temporal is not None and (
        temporal.get("status") != "passed" or execution.get("properties", {}).get("status") != "Succeeded"
    ):
        return None
    label = {"reused_from_record": record["record_sha256"], "reused_vendor_digest": current_digest}
    files = {"wc124-vendor-migrations.json": {**migrations, **label}}
    if temporal is not None:
        files["wc124-temporal-pool-evidence.json"] = {**temporal, **label}
        files["wc124-temporal-startup-execution.json"] = execution
    return files


def decide_path(
    record: dict[str, Any] | None,
    *,
    repository_files: Mapping[str, str],
    classification: Mapping[str, Mapping[str, Any]],
    payload_bytes: int,
    requested: str,
    **binding: Any,
) -> dict[str, Any]:
    """Choose reuse, update or full; the repository and the record are the only inputs (no database)."""
    decision: dict[str, Any] = {"path": "full", "reason": "unknown", "added_files": []}
    if binding.get("environment") not in {"demo", "uat"}:
        decision["path"] = "refused"
        decision["reason"] = (
            "Production database path is designed (update first, restore marker, full only with Founder "
            "approval) but not enabled: Production apply is separately prohibited"
        )
        return decision
    if requested not in {"auto", "full"}:
        decision["reason"] = f"database_path {requested!r} is not recognised"
        return decision
    if requested == "full":
        decision["reason"] = "database_path=full requested"
        return decision
    if record is None:
        decision["reason"] = "no record exists"
        return decision
    reason = reject_reason(record, **binding)
    if reason is not None:
        decision["reason"] = reason
        return decision
    applied = record["applied_init_files"]
    changed = sorted(name for name, digest in applied.items() if repository_files.get(name, digest) != digest)
    removed = sorted(name for name in applied if name not in repository_files)
    if changed or removed:
        decision["reason"] = f"applied init files changed or removed: {', '.join(changed + removed)}"
        return decision
    added = sorted((name for name in repository_files if name not in applied), key=str.encode)
    if not added:
        return {"path": "reuse", "reason": "every binding matches the recorded chain and no init file is new", "added_files": []}
    last_applied = max(applied, key=str.encode)
    early = [name for name in added if name.encode() < last_applied.encode()]
    if early:
        decision["reason"] = f"new init files sort before applied file {last_applied}: {', '.join(early)}"
        return decision
    refused = [
        f"{name} ({info.get('class')}; {', '.join(info.get('findings', [])) or 'no findings'})"
        for name in added
        for info in [classification.get(name, {})]
        if info.get("class") != "update" or info.get("findings") or info.get("sha256") != repository_files[name]
    ]
    if refused:
        decision["reason"] = f"new init files cannot use the update path: {'; '.join(refused)}"
        return decision
    if payload_bytes > MAX_UPDATE_PAYLOAD_BYTES:
        decision["reason"] = f"update payload is {payload_bytes} bytes, above {MAX_UPDATE_PAYLOAD_BYTES}"
        return decision
    principal = record["provisioner_result"].get("update_principal")
    if not isinstance(principal, dict) or principal.get("memberships") != sorted(UPDATE_OWNER_ROLES):
        decision["reason"] = "the recorded provisioning did not create the update principal with its exact memberships"
        return decision
    return {
        "path": "update",
        "reason": f"{len(added)} new update-class init file(s) pass every rule",
        "added_files": added,
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


def vendor_from_files(arguments: argparse.Namespace) -> dict[str, Any] | None:
    """Vendor qualification evidence of this run, when it ran (the files are restored, not new, when skipped)."""
    migrations = getattr(arguments, "vendor_migrations", None)
    digest = getattr(arguments, "vendor_digest", "")
    if migrations is None or not migrations.is_file() or not digest:
        return None
    pool = getattr(arguments, "temporal_pool", None)
    execution = getattr(arguments, "temporal_execution", None)
    has_temporal = pool is not None and pool.is_file() and execution is not None and execution.is_file()
    return {
        "digest": digest,
        "migrations": load_object(migrations),
        "temporal_pool": load_object(pool) if has_temporal else None,
        "temporal_execution": load_object(execution) if has_temporal else None,
    }


def command_create(arguments: argparse.Namespace) -> int:
    record = create_record(
        environment=arguments.environment,
        fingerprint=arguments.fingerprint,
        live_facts=load_object(arguments.live_facts),
        provisioner_result=load_object(arguments.provisioner_result),
        provisioner_execution=load_object(arguments.provisioner_execution),
        run_id=arguments.run_id,
        recorded_at=datetime.now(timezone.utc),
        applied_init_files=init_file_digests(arguments.repository_root),
        vendor=vendor_from_files(arguments),
        checkpoint=make_checkpoint(arguments.release_sha, arguments.run_id),
    )
    arguments.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def command_refresh(arguments: argparse.Namespace) -> int:
    """Rewrite the record after a successful update or vendor qualification."""
    previous = load_object(arguments.previous_record)
    applied = dict(previous["applied_init_files"])
    digests = init_file_digests(arguments.repository_root)
    for name in arguments.added_file:
        applied[name] = digests[name]
    record = refresh_record(
        previous,
        run_id=arguments.run_id,
        recorded_at=datetime.now(timezone.utc),
        applied_init_files=applied,
        vendor=vendor_from_files(arguments),
        checkpoint=make_checkpoint(arguments.release_sha, arguments.run_id),
    )
    arguments.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def write_json(directory: Path, name: str, content: Any) -> None:
    (directory / name).write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_vendor_plan(arguments: argparse.Namespace) -> int:
    """Decide, after the migration plan exists, whether the vendor migrations and Temporal qualification may be skipped."""
    decision: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "vendor_reuse": False,
        "vendor_digest": "",
        "reason": "unknown",
    }
    try:
        plan = load_object(arguments.plan)
        digest = vendor_qualification_digest(arguments.repository_root, plan)
        decision["vendor_digest"] = digest
        record = load_object(arguments.record) if arguments.record.is_file() else None
        if arguments.database_path not in {"reuse", "update"} or record is None:
            decision["reason"] = "the database chain ran in full or no record exists"
        else:
            files = vendor_reuse_evidence(record, digest, arguments.database_path)
            if files is None:
                decision["reason"] = "no equal recorded qualification (vendor definitions or evidence differ)"
            else:
                for name, content in files.items():
                    write_json(arguments.output_directory, name, content)
                decision.update(
                    {"vendor_reuse": True, "reason": "recorded vendor, PgBouncer and job-definition digests are unchanged"}
                )
    except (OSError, ValueError, KeyError, TypeError) as error:
        decision["reason"] = f"vendor reuse could not be evaluated: {type(error).__name__}"
    print(json.dumps(decision, sort_keys=True))
    return 0


def command_evaluate(arguments: argparse.Namespace) -> int:
    """Always prints a decision; any error or doubt means the full chain runs."""
    decision: dict[str, Any] = {"reuse": False, "path": "full", "reason": "unknown"}
    try:
        now = datetime.now(timezone.utc)
        record = load_object(arguments.record) if arguments.record.is_file() else None
        files = init_file_digests(arguments.repository_root)
        applied = record.get("applied_init_files") if isinstance(record, dict) else None
        added = sorted((name for name in files if name not in applied), key=str.encode) if isinstance(applied, dict) else []
        payload, manifest = update_payload(arguments.repository_root, added) if added else ("", "")
        chosen = decide_path(
            record,
            repository_files=files,
            classification=classify_files(arguments.repository_root, added),
            payload_bytes=len(payload),
            requested=arguments.database_path,
            environment=arguments.environment,
            fingerprint=arguments.fingerprint,
            live_facts=load_object(arguments.live_facts),
            now=now,
            reset_requested=arguments.reset_requested == "true",
            transition_state=str(load_object(arguments.transition).get("state")),
            expected_spend_paise=arguments.expected_spend_paise,
        )
        decision.update(chosen)
        decision["reuse"] = chosen["path"] in {"reuse", "update"}
        if decision["reuse"]:
            assert record is not None
            for name, content in reuse_evidence(record, now, chosen["path"]).items():
                write_json(arguments.output_directory, name, content)
        decision["resume"] = resume_decision(
            record,
            requested=arguments.resume_from,
            release_sha=arguments.release_sha,
            path=chosen["path"],
        )
        if chosen["path"] == "update":
            (arguments.output_directory / "wc177-database-update-payload.b64").write_text(payload, encoding="utf-8")
            (arguments.output_directory / "wc177-database-update-manifest.txt").write_text(manifest, encoding="utf-8")
            decision["manifest_sha256"] = hashlib.sha256(manifest.encode()).hexdigest()
            decision["payload_bytes"] = len(payload)
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as error:
        decision = {
            "reuse": False,
            "path": "full",
            "reason": f"record could not be evaluated: {type(error).__name__}",
            "added_files": [],
        }
    decision["schema"] = PLAN_SCHEMA
    print(json.dumps(decision, sort_keys=True))
    return 3 if decision["path"] == "refused" else 0


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
    create.add_argument("--repository-root", type=Path, default=Path("."))
    create.add_argument("--vendor-migrations", type=Path)
    create.add_argument("--vendor-digest", default="")
    create.add_argument("--temporal-pool", type=Path)
    create.add_argument("--temporal-execution", type=Path)
    create.add_argument("--release-sha", default="")
    create.set_defaults(handler=command_create)

    refresh = commands.add_parser("refresh")
    refresh.add_argument("--previous-record", required=True, type=Path)
    refresh.add_argument("--run-id", required=True)
    refresh.add_argument("--output", required=True, type=Path)
    refresh.add_argument("--repository-root", type=Path, default=Path("."))
    refresh.add_argument("--added-file", action="append", default=[])
    refresh.add_argument("--vendor-migrations", type=Path)
    refresh.add_argument("--vendor-digest", default="")
    refresh.add_argument("--temporal-pool", type=Path)
    refresh.add_argument("--temporal-execution", type=Path)
    refresh.add_argument("--release-sha", default="")
    refresh.set_defaults(handler=command_refresh)

    vendor_plan = commands.add_parser("vendor-plan")
    vendor_plan.add_argument("--record", required=True, type=Path)
    vendor_plan.add_argument("--plan", required=True, type=Path)
    vendor_plan.add_argument("--database-path", required=True)
    vendor_plan.add_argument("--repository-root", type=Path, default=Path("."))
    vendor_plan.add_argument("--output-directory", required=True, type=Path)
    vendor_plan.set_defaults(handler=command_vendor_plan)

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("--record", required=True, type=Path)
    evaluate.add_argument("--environment", required=True)
    evaluate.add_argument("--fingerprint", required=True)
    evaluate.add_argument("--live-facts", required=True, type=Path)
    evaluate.add_argument("--transition", required=True, type=Path)
    evaluate.add_argument("--reset-requested", required=True, choices=("true", "false"))
    evaluate.add_argument("--database-path", default="auto")
    evaluate.add_argument("--resume-from", default="start")
    evaluate.add_argument("--release-sha", default="")
    evaluate.add_argument("--repository-root", type=Path, default=Path("."))
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

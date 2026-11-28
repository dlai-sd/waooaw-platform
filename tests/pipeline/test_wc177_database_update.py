"""WC-177: database path plan, update-class lint rules, update principal, update job and workflow wiring."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

import wc124_db_provisioner as provisioner
import wc124_init_chain_lint as lint
import wc143_database_chain_record as chain
import wc177_database_update_job as update_job
import wc177_stage_timings as timings
from test_wc124_pre_activation_evidence import passing_identity, passing_temporal, succeeded
from wc124_pre_activation_evidence import validate_evidence

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_TEXT = (ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
WORKFLOW = yaml.safe_load(WORKFLOW_TEXT)
STEPS = {step["name"]: step for step in WORKFLOW["jobs"]["terraform"]["steps"] if "name" in step}
STEP_ORDER = [step["name"] for step in WORKFLOW["jobs"]["terraform"]["steps"] if "name" in step]
NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
FIXTURE = "99zzzzzzzz-wc177-fixture.sql"
GOOD_UPDATE = """-- wc177-apply: update
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;
CREATE TABLE IF NOT EXISTS business.wc177_probe (probe_id uuid PRIMARY KEY);
GRANT SELECT ON business.wc177_probe TO business_app;
"""


def rules(text: str) -> set[str]:
    return {finding.rule for finding in lint.update_rule_findings("x.sql", text)}


def test_a_compliant_update_file_has_no_findings() -> None:
    assert lint.declared_class(GOOD_UPDATE) == "update"
    assert lint.lint_sql("x.sql", GOOD_UPDATE) == []
    assert rules(GOOD_UPDATE) == set()


@pytest.mark.parametrize(
    ("statement", "rule"),
    [
        ("DROP TABLE business.old;", "drop-not-allowed"),
        ("TRUNCATE business.x;", "truncate-or-delete-not-allowed"),
        ("ALTER TABLE business.x RENAME TO y;", "rename-not-allowed"),
        ("ALTER TABLE business.x ALTER COLUMN a TYPE bigint;", "column-type-change-not-allowed"),
        ("ALTER TABLE business.x ADD COLUMN IF NOT EXISTS a int NOT NULL;", "not-null-column-without-default"),
        ("CREATE ROLE sneaky NOLOGIN;", "role-change-not-allowed"),
        ("GRANT bp_owner TO business_app;", "role-membership-not-allowed"),
        ("CREATE EXTENSION IF NOT EXISTS pgcrypto;", "extension-not-allowed"),
        ("ALTER TABLE business.x OWNER TO ce_owner;", "other-owner-referenced"),
        ("UPDATE business.x SET a = 1;", "unbounded-update"),
        ("COMMIT;", "transaction-control"),
        ("SET ROLE bp_owner;", "set-role-without-local"),
        ("VACUUM business.x;", "statement-not-allowed"),
    ],
)
def test_each_update_rule_rejects_its_statement(statement: str, rule: str) -> None:
    assert rule in rules(GOOD_UPDATE + statement + "\n")


def test_update_files_must_set_a_role_and_timeouts_before_changing_anything() -> None:
    no_role = "-- wc177-apply: update\nSET LOCAL lock_timeout = '5s';\nSET LOCAL statement_timeout = '5s';\nCREATE TABLE IF NOT EXISTS a.b (c int);\n"
    assert "statement-without-set-local-role" in rules(no_role)
    no_timeouts = "-- wc177-apply: update\nSET LOCAL ROLE wbe_owner;\nCREATE TABLE IF NOT EXISTS a.b (c int);\n"
    assert "missing-lock-or-statement-timeout" in rules(no_timeouts)
    assert "set-role-outside-update-owners" in rules(GOOD_UPDATE.replace("bp_owner;", "billing_owner;", 1))
    assert "psql-meta-command" in rules(GOOD_UPDATE + "\\connect other\n")


def test_a_file_without_the_header_is_full_class_and_existing_files_are_untouched() -> None:
    directory = ROOT / "infrastructure/postgres/init"
    texts = [path.read_text(encoding="utf-8") for path in directory.glob("*.sql")]
    assert texts and all(lint.declared_class(text) == "full" for text in texts)
    findings, _ = lint.lint_directory(directory)
    baseline = [
        item for path in sorted(directory.glob("*.sql")) for item in lint.lint_sql(path.name, path.read_text(encoding="utf-8"))
    ]
    assert len(findings) == len(baseline)  # no update-class rule is applied to a file without the header
    assert lint.declared_class("-- wc177-apply: maybe\nSELECT 1;") == "full"


def seeded(tmp_path: Path, extra: dict[str, str] | None = None) -> Path:
    init = tmp_path / chain.INIT_DIRECTORY
    init.mkdir(parents=True)
    (init / chain.BOOTSTRAP_FILE).write_text("-- bootstrap\n", encoding="utf-8")
    (init / "01-base.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (init / "02-base.sql").write_text("SELECT 2;\n", encoding="utf-8")
    for name, text in (extra or {}).items():
        (init / name).write_text(text, encoding="utf-8")
    return tmp_path


def record_for(root: Path, **overrides: object) -> dict:
    body = {
        "environment": "demo",
        "fingerprint": "f" * 64,
        "live_facts": {"environment": "demo"},
        "provisioner_result": {
            **passing_identity("exec-1"),
            "schema": chain.PROVISIONER_RESULT_SCHEMA,
            "database_reset": None,
            "update_principal": {"memberships": ["bp_owner", "wbe_owner"]},
        },
        "provisioner_execution": succeeded("exec-1"),
        "run_id": "1",
        "recorded_at": NOW - timedelta(hours=1),
        "applied_init_files": chain.init_file_digests(root),
    }
    body.update(overrides)
    return chain.create_record(**body)


def plan(root: Path, record: dict | None, requested: str = "auto", **overrides: object) -> dict:
    files = chain.init_file_digests(root)
    applied = record["applied_init_files"] if record else {}
    added = sorted((name for name in files if name not in applied), key=str.encode)
    payload, _ = chain.update_payload(root, added) if added else ("", "")
    arguments: dict = {
        "environment": "demo",
        "fingerprint": "f" * 64,
        "live_facts": {"environment": "demo"},
        "now": NOW,
        "reset_requested": False,
        "transition_state": "REVOKED",
        "expected_spend_paise": None,
    }
    arguments.update(overrides)
    return chain.decide_path(
        record,
        repository_files=files,
        classification=chain.classify_files(root, added),
        payload_bytes=len(payload),
        requested=requested,
        **arguments,
    )


def test_unchanged_repository_selects_reuse(tmp_path: Path) -> None:
    root = seeded(tmp_path)
    assert plan(root, record_for(root))["path"] == "reuse"


def test_one_new_declared_clean_file_selects_update(tmp_path: Path) -> None:
    root = seeded(tmp_path)
    record = record_for(root)
    (root / chain.INIT_DIRECTORY / FIXTURE).write_text(GOOD_UPDATE, encoding="utf-8")
    decision = plan(root, record)
    assert decision["path"] == "update" and decision["added_files"] == [FIXTURE]


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        (GOOD_UPDATE.split("\n", 1)[1], "full"),
        ("-- wc177-apply: maybe\n" + GOOD_UPDATE.split("\n", 1)[1], "full"),
        (GOOD_UPDATE + "DROP TABLE business.old;\n", "drop-not-allowed"),
        (GOOD_UPDATE.replace("IF NOT EXISTS ", ""), "create-without-if-not-exists"),
    ],
)
def test_new_files_that_cannot_use_update_select_full(tmp_path: Path, text: str, reason: str) -> None:
    root = seeded(tmp_path)
    record = record_for(root)
    (root / chain.INIT_DIRECTORY / FIXTURE).write_text(text, encoding="utf-8")
    decision = plan(root, record)
    assert decision["path"] == "full" and reason in decision["reason"]


def test_every_fail_closed_input_selects_full(tmp_path: Path) -> None:
    root = seeded(tmp_path)
    record = record_for(root)
    assert plan(root, None)["reason"] == "no record exists"
    assert "requested" in plan(root, record, "full")["reason"]
    assert "not recognised" in plan(root, record, "fast")["reason"]
    assert "reset" in plan(root, record, reset_requested=True)["reason"]
    assert "fingerprint" in plan(root, record, fingerprint="0" * 64)["reason"]
    assert "live database" in plan(root, record, live_facts={"environment": "other"})["reason"]
    assert "older than" in plan(root, record, now=NOW + timedelta(days=8))["reason"]
    (root / chain.INIT_DIRECTORY / "01-base.sql").write_text("SELECT 11;\n", encoding="utf-8")
    assert "changed or removed" in plan(root, record)["reason"]
    (root / chain.INIT_DIRECTORY / "01-base.sql").unlink()
    assert "changed or removed" in plan(root, record)["reason"]


def test_a_new_file_sorting_before_an_applied_file_selects_full(tmp_path: Path) -> None:
    root = seeded(tmp_path)
    record = record_for(root)
    (root / chain.INIT_DIRECTORY / "00a-early.sql").write_text(GOOD_UPDATE, encoding="utf-8")
    assert "sort before" in plan(root, record)["reason"]


def test_oversized_payload_and_missing_update_principal_select_full(tmp_path: Path) -> None:
    root = seeded(tmp_path)
    record = record_for(root)
    (root / chain.INIT_DIRECTORY / FIXTURE).write_text(GOOD_UPDATE, encoding="utf-8")
    files = chain.init_file_digests(root)
    big = chain.decide_path(
        record,
        repository_files=files,
        classification=chain.classify_files(root, [FIXTURE]),
        payload_bytes=chain.MAX_UPDATE_PAYLOAD_BYTES + 1,
        requested="auto",
        environment="demo",
        fingerprint="f" * 64,
        live_facts={"environment": "demo"},
        now=NOW,
        reset_requested=False,
        transition_state="REVOKED",
        expected_spend_paise=None,
    )
    assert big["path"] == "full" and "payload" in big["reason"]
    stripped = copy.deepcopy(record)
    del stripped["record_sha256"]
    del stripped["provisioner_result"]["update_principal"]
    assert "update principal" in plan(root, chain.seal(stripped))["reason"]


def test_version_1_record_selects_full_once(tmp_path: Path) -> None:
    root = seeded(tmp_path)
    legacy = {key: value for key, value in record_for(root).items() if key != "record_sha256"}
    legacy["schema"] = chain.LEGACY_RECORD_SCHEMA
    assert "version 1" in plan(root, chain.seal(legacy))["reason"]


def test_production_is_refused_by_the_plan_and_the_command(tmp_path: Path) -> None:
    root = seeded(tmp_path)
    assert plan(root, record_for(root), environment="prod")["path"] == "refused"
    record = tmp_path / "record.json"
    record.write_text(json.dumps(record_for(root)), encoding="utf-8")
    (tmp_path / "facts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "transition.json").write_text('{"state": "REVOKED"}', encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts/wc143_database_chain_record.py"), "evaluate",
            "--record", str(record), "--environment", "prod", "--fingerprint", "f" * 64,
            "--live-facts", str(tmp_path / "facts.json"), "--transition", str(tmp_path / "transition.json"),
            "--reset-requested", "false", "--repository-root", str(root), "--output-directory", str(tmp_path),
        ],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert completed.returncode == 3 and json.loads(completed.stdout)["path"] == "refused"


def test_evaluate_writes_the_update_payload_and_labelled_reuse_evidence(tmp_path: Path) -> None:
    root = seeded(tmp_path / "repo")
    record = record_for(root, recorded_at=datetime.now(timezone.utc) - timedelta(hours=1))
    (root / chain.INIT_DIRECTORY / FIXTURE).write_text(GOOD_UPDATE, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "record.json").write_text(json.dumps(record), encoding="utf-8")
    (out / "facts.json").write_text(json.dumps({"environment": "demo"}), encoding="utf-8")
    (out / "transition.json").write_text('{"state": "REVOKED"}', encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts/wc143_database_chain_record.py"), "evaluate",
            "--record", str(out / "record.json"), "--environment", "demo", "--fingerprint", "f" * 64,
            "--live-facts", str(out / "facts.json"), "--transition", str(out / "transition.json"),
            "--reset-requested", "false", "--repository-root", str(root), "--output-directory", str(out),
            "--resume-from", "activation", "--release-sha", "abc",
        ],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    decision = json.loads(completed.stdout)
    assert completed.returncode == 0 and decision["path"] == "update" and decision["reuse"] is True
    manifest = (out / "wc177-database-update-manifest.txt").read_text(encoding="utf-8")
    assert hashlib_sha(manifest) == decision["manifest_sha256"] and FIXTURE in manifest
    assert (out / "wc177-database-update-payload.b64").read_text(encoding="utf-8")
    reuse = json.loads((out / "wc143-database-chain-reuse.json").read_text(encoding="utf-8"))
    assert reuse["database_path"] == "update" and decision["resume"]["honoured"] is False


def hashlib_sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


def test_update_payload_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    import base64
    import io
    import tarfile

    root = seeded(tmp_path, {FIXTURE: GOOD_UPDATE})
    first = chain.update_payload(root, [FIXTURE])
    assert first == chain.update_payload(root, [FIXTURE])
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(first[0])), mode="r:gz") as archive:
        assert archive.extractfile(FIXTURE).read().decode() == GOOD_UPDATE
    assert first[1] == f"{hashlib_sha(GOOD_UPDATE)}  {FIXTURE}\n"


def test_refresh_keeps_chain_evidence_and_adds_applied_files(tmp_path: Path) -> None:
    root = seeded(tmp_path)
    previous = record_for(root)
    (root / chain.INIT_DIRECTORY / FIXTURE).write_text(GOOD_UPDATE, encoding="utf-8")
    applied = dict(previous["applied_init_files"]) | {FIXTURE: chain.init_file_digests(root)[FIXTURE]}
    refreshed = chain.refresh_record(previous, run_id="2", recorded_at=NOW, applied_init_files=applied)
    assert refreshed["provisioner_result"] == previous["provisioner_result"]
    assert refreshed["previous_record_sha256"] == previous["record_sha256"] and FIXTURE in refreshed["applied_init_files"]
    assert plan(root, refreshed)["path"] == "reuse"


def test_fingerprint_ignores_new_init_files_but_follows_the_bootstrap(tmp_path: Path) -> None:
    root = tmp_path
    for name in chain.CHAIN_INPUTS:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(name, encoding="utf-8")
    (root / chain.INIT_DIRECTORY / "99-new.sql").write_text("x", encoding="utf-8")
    first = chain.chain_fingerprint(root, "demo")
    (root / chain.INIT_DIRECTORY / "98-other.sql").write_text("y", encoding="utf-8")
    assert chain.chain_fingerprint(root, "demo") == first
    (root / chain.INIT_DIRECTORY / chain.BOOTSTRAP_FILE).write_text("changed", encoding="utf-8")
    assert chain.chain_fingerprint(root, "demo") != first


def vendor_plan(marker: str = "a") -> dict:
    return {
        "resource_changes": [
            {
                "address": address,
                "change": {"after": {"template": [marker, address], "secret": [], "identity": []}, "after_unknown": {}},
            }
            for address in chain.VENDOR_ADDRESSES
        ]
    }


def test_vendor_digest_follows_planned_definitions_and_reuse_needs_recorded_success() -> None:
    assert chain.plan_definition_digest(vendor_plan("a")) == chain.plan_definition_digest(vendor_plan("a"))
    assert chain.plan_definition_digest(vendor_plan("a")) != chain.plan_definition_digest(vendor_plan("b"))
    with pytest.raises(ValueError, match="none of the vendor resources"):
        chain.plan_definition_digest({"resource_changes": []})
    digest = chain.vendor_qualification_digest(ROOT, vendor_plan("a"))
    vendor = {
        "digest": digest,
        "migrations": {"executions": [{"component": "keycloak", "status": "Succeeded"}]},
        "temporal_pool": {"status": "passed"},
        "temporal_execution": succeeded("temporal-1"),
    }
    record = {"vendor": vendor, "record_sha256": "r" * 64, "environment": "demo"}
    files = chain.vendor_reuse_evidence(record, digest, "reuse")
    assert files and files["wc124-vendor-migrations.json"]["reused_from_record"] == "r" * 64
    assert chain.vendor_reuse_evidence(record, digest, "full") is None
    assert chain.vendor_reuse_evidence(record, "0" * 64, "reuse") is None
    failed = copy.deepcopy(record)
    failed["vendor"]["migrations"]["executions"][0]["status"] = "Failed"
    assert chain.vendor_reuse_evidence(failed, digest, "reuse") is None
    no_temporal = copy.deepcopy(record)
    no_temporal["vendor"]["temporal_pool"] = no_temporal["vendor"]["temporal_execution"] = None
    assert chain.vendor_reuse_evidence(no_temporal, digest, "reuse") is None


def test_resume_is_honoured_only_for_an_intact_checkpoint_of_the_same_release(tmp_path: Path) -> None:
    record = {"checkpoint": chain.make_checkpoint("sha-1", "9")}
    honoured = chain.resume_decision(record, requested="activation", release_sha="sha-1", path="reuse")
    assert honoured["honoured"] is True
    for kwargs in (
        {"release_sha": "sha-2", "path": "reuse"},
        {"release_sha": "sha-1", "path": "full"},
        {"release_sha": "", "path": "reuse"},
    ):
        assert chain.resume_decision(record, requested="activation", **kwargs)["honoured"] is False
    assert chain.resume_decision(None, requested="activation", release_sha="sha-1", path="reuse")["honoured"] is False
    assert chain.resume_decision(record, requested="start", release_sha="sha-1", path="reuse")["honoured"] is False


def update_evidence(record_sha: str = "r" * 64) -> dict:
    return {
        "schema": "waooaw.wc177-database-update/v1",
        "status": "applied-verified",
        "execution": "update-1",
        "record_sha256": record_sha,
        "result": {"status": "passed", "memberships": "bp_owner,wbe_owner"},
    }


def accepted(**overrides: object) -> dict:
    reuse = {"execution": "exec-1", "record_sha256": "r" * 64, "database_path": "update"}
    arguments: dict = {
        "environment": "demo",
        "identity": passing_identity("exec-1"),
        "identity_execution": succeeded("exec-1"),
        "temporal": passing_temporal(),
        "temporal_execution": succeeded("temporal-current"),
        "chain_reuse": reuse,
        "database_update": update_evidence(),
    }
    arguments.update(overrides)
    return validate_evidence(**arguments)


def test_the_update_path_is_accepted_only_with_bound_update_evidence() -> None:
    result = accepted()
    assert result["database_path"] == "update" and result["database_update_execution"] == "update-1"
    with pytest.raises(ValueError, match="requires database update evidence"):
        accepted(database_update=None)
    with pytest.raises(ValueError, match="different chain record"):
        accepted(database_update=update_evidence("0" * 64))
    with pytest.raises(ValueError, match="did not pass"):
        accepted(database_update={**update_evidence(), "result": {"status": "passed", "memberships": "bp_owner"}})
    with pytest.raises(ValueError, match="did not choose the update path"):
        accepted(chain_reuse={"execution": "exec-1", "record_sha256": "r" * 64, "database_path": "reuse"})
    assert (
        accepted(chain_reuse={"execution": "exec-1", "record_sha256": "r" * 64}, database_update=None)["database_path"] == "reuse"
    )


def job_definition(**changes: object) -> dict:
    job = {
        "name": "job-demo-wc124-database-update",
        "resourceGroup": "waooaw-demo-rg",
        "type": "Microsoft.App/jobs",
        "id": "/subscriptions/sub/resourceGroups/waooaw-demo-rg/providers/Microsoft.App/jobs/job-demo-wc124-database-update",
        "properties": {
            "configuration": {
                "secrets": [
                    {"name": "update-database", "keyVaultUrl": "https://kv-demo.vault.azure.net/secrets/db-database-update/v1"}
                ]
            },
            "template": {
                "containers": [
                    {
                        "name": "database-update",
                        "image": "docker.io/library/postgres@sha256:" + "a" * 64,
                        "resources": {"cpu": 0.25, "memory": "0.5Gi"},
                        "env": [{"name": "DATABASE_URL", "secretRef": "update-database"}],
                    }
                ]
            },
        },
    }
    job.update(changes)
    return job


def build_template(job: dict) -> dict:
    manifest = f"{'b' * 64}  {FIXTURE}\n"
    return update_job.build_update_template(
        job,
        environment="demo",
        subscription_id="sub",
        script=(ROOT / "scripts/wc177_database_update.sh").read_text(encoding="utf-8"),
        payload_b64="cGF5bG9hZA==",
        manifest=manifest,
        manifest_sha256=hashlib_sha(manifest),
    )


def test_the_start_template_carries_the_reviewed_program_and_payload_only() -> None:
    container = build_template(job_definition())["containers"][0]
    assert container["command"] == ["/bin/sh", "-c"] and container["args"][0].startswith("#!/bin/sh\n")
    names = {item["name"] for item in container["env"]}
    assert names == {"DATABASE_URL", "UPDATE_PAYLOAD_B64", "UPDATE_MANIFEST", "UPDATE_MANIFEST_SHA256"}
    assert not any(item.get("value", "").endswith("\n") for item in container["env"])


@pytest.mark.parametrize(
    "change",
    [
        {"name": "job-demo-wc124-billing-migration"},
        {"resourceGroup": "waooaw-uat-rg"},
        {"type": "Microsoft.App/containerApps"},
    ],
)
def test_the_template_builder_refuses_a_job_outside_its_scope(change: dict) -> None:
    with pytest.raises(ValueError, match="outside its environment scope"):
        build_template(job_definition(**change))


def test_the_template_builder_refuses_an_unpinned_image_secret_or_tampered_manifest() -> None:
    job = job_definition()
    job["properties"]["template"]["containers"][0]["image"] = "docker.io/library/postgres:16"
    with pytest.raises(ValueError, match="immutable postgres image"):
        build_template(job)
    job = job_definition()
    job["properties"]["configuration"]["secrets"][0]["keyVaultUrl"] = "https://kv.vault.azure.net/secrets/other/v1"
    with pytest.raises(ValueError, match="Key Vault reference"):
        build_template(job)
    with pytest.raises(ValueError, match="manifest does not match"):
        update_job.build_update_template(
            job_definition(), environment="demo", subscription_id="sub", script="#!/bin/sh\n",
            payload_b64="x", manifest="m\n", manifest_sha256="0" * 64,
        )  # fmt: skip
    with pytest.raises(ValueError, match="restricted to Demo and UAT"):
        update_job.job_name("prod")


def test_the_apply_program_is_valid_posix_shell_and_refuses_by_design() -> None:
    script = ROOT / "scripts/wc177_database_update.sh"
    assert subprocess.run(["sh", "-n", str(script)], check=False).returncode == 0
    text = script.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n")
    for token in (
        "WC177_UPDATE_REFUSED",
        "--single-transaction",
        "RESET ROLE",
        "WC177_UPDATE_LOCK_TIMEOUT",
        "bp_owner,wbe_owner",
    ):
        assert token in text


class FakePsql:
    def __init__(self, state: dict) -> None:
        self.state = state
        self.statements: list[str] = []

    def __call__(self, _server, _bootstrap, _database, _token, sql, *, tuples_only=False) -> str:
        self.statements.append(sql)
        if tuples_only and "json_build_object" in sql:
            return json.dumps(self.state)
        if tuples_only:
            return "3\n" if not any("REASSIGN" in item for item in self.statements) else "0\n"
        return ""


def good_state() -> dict:
    return {
        "memberships": ["bp_owner", "wbe_owner"],
        "superuser": False,
        "createrole": False,
        "createdb": False,
        "bypassrls": False,
        "inherit": False,
        "login": True,
        "wbe_owner_exists": True,
    }


def test_the_update_principal_is_created_with_exactly_its_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakePsql(good_state())
    monkeypatch.setattr(provisioner, "psql", fake)
    result = provisioner.provision_update_principal("server", "bootstrap-principal", "token")
    sql = "\n".join(fake.statements)
    assert sql.index("GRANT bp_owner TO") < sql.index("REASSIGN OWNED BY") < sql.index("REVOKE bp_owner FROM")
    assert 'ALTER ROLE "database_updater" NOINHERIT;' in sql
    assert "GRANT wbe_owner TO" in sql and "GRANT SELECT, INSERT, UPDATE ON wc124_provisioning.init_chain_ledger" in sql
    assert result == {
        "principal": "database_updater",
        "memberships": ["bp_owner", "wbe_owner"],
        "bootstrap_owned_objects_before": 3,
        "bootstrap_owned_objects_after": 0,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"superuser": True},
        {"createrole": True},
        {"inherit": True},
        {"memberships": ["bp_owner"]},
        {"memberships": ["bp_owner", "ce_owner", "wbe_owner"]},
    ],
)
def test_the_update_principal_is_rejected_when_it_holds_more_or_less(monkeypatch: pytest.MonkeyPatch, change: dict) -> None:
    monkeypatch.setattr(provisioner, "psql", FakePsql({**good_state(), **change}))
    with pytest.raises(ValueError, match="beyond the update class"):
        provisioner.provision_update_principal("server", "bootstrap-principal", "token")


def test_the_update_principal_is_declared_everywhere_it_must_be() -> None:
    spec = next(item for item in provisioner.environment_specs("uat") if item.role == provisioner.UPDATE_PRINCIPAL)
    assert spec.secret_id == "db-database-update" and spec.database == provisioner.APPLICATION_DATABASE
    catalog = json.loads((ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text(encoding="utf-8"))
    assert provisioner.validate_catalog(catalog, "demo") and provisioner.validate_catalog(catalog, "uat")
    assert "'database_updater'" in (ROOT / "infrastructure/postgres/init" / provisioner.PRINCIPAL_BOOTSTRAP_NAME).read_text(
        encoding="utf-8"
    )
    variables = (ROOT / "infrastructure/terraform/phase2/modules/workload/variables.tf").read_text(encoding="utf-8")
    assert variables.count('"database-update"') == 2
    module = (ROOT / "infrastructure/terraform/phase2/modules/workload/main.tf").read_text(encoding="utf-8")
    assert (
        'resource "azurerm_container_app_job" "database_update"' in module
        and "job-${var.environment}-wc124-database-update" in module
    )
    assert "-target=module.workload.azurerm_container_app_job.database_update[0]" in WORKFLOW_TEXT


def test_an_auth_file_written_before_the_update_principal_existed_is_extended(monkeypatch: pytest.MonkeyPatch) -> None:
    specs = provisioner.environment_specs("uat")
    passwords = {spec.role: f"pw-{index}" for index, spec in enumerate(specs)}
    existing_auth = provisioner.authfile_value(
        {role: pw for role, pw in passwords.items() if role != provisioner.UPDATE_PRINCIPAL}
    )

    def fake_run(command, **_kwargs):
        name = command[command.index("--name") + 1]
        spec = next(item for item in specs if item.vault_name == name)
        if spec.role == provisioner.UPDATE_PRINCIPAL:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="SecretNotFound")
        value = (
            existing_auth
            if spec.value_format == "authfile"
            else provisioner.secret_value(spec, passwords[spec.role], "pgbouncer")
        )
        record = {
            "attributes": {"enabled": True},
            "tags": {"wc124-role": spec.role, "wc124-database": spec.database},
            "value": value,
            "id": f"https://kv/secrets/{name}/v1",
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(record), stderr="")

    monkeypatch.setattr(provisioner.subprocess, "run", fake_run)
    monkeypatch.setattr(provisioner, "generate_password", lambda: "generated-update-password")
    read, records = provisioner.read_credentials(specs, "kv-demo")
    assert read[provisioner.UPDATE_PRINCIPAL] == "generated-update-password"
    auth_spec = next(spec for spec in specs if spec.value_format == "authfile")
    assert records[auth_spec.secret_id]["value"] != provisioner.authfile_value(read)


def job_steps(*names: str) -> list[dict]:
    return [
        {"name": name, "started_at": "2026-11-28T10:00:00Z", "completed_at": "2026-11-28T10:01:30Z", "conclusion": "success"}
        for name in names
    ]


def test_stage_timings_report_path_reason_and_seconds_and_name_real_steps() -> None:
    for names in timings.STAGE_GROUPS.values():
        for name in names:
            assert name in STEPS, name
    for name in timings.VENDOR_MARKERS.values():
        assert name in STEPS
    assert timings.RECORD_STEP in STEPS
    steps = job_steps("Terraform foundation plan", "Run WC-124 database provisioner")
    steps.append({"name": "Run vendor schema migrations against private PostgreSQL", "conclusion": "skipped"})
    report = timings.build_report({"steps": steps}, database_path="update", reason="one new file", environment="demo", run_id="1")
    assert report["groups"]["database"] == {
        "seconds": 90,
        "steps_run": 1,
        "steps_skipped": 0,
        "path": "update",
        "reason": "one new file",
    }
    assert report["groups"]["vendor_migrations"]["path"] == "skipped-by-proof"
    assert report["groups"]["terraform"]["seconds"] == 90 and report["baseline_run"] == "45983274213"
    assert any("| database | update | 90 |" in line for line in timings.summary_lines(report))


def test_workflow_inputs_and_dispatch_carry_database_path_and_resume() -> None:
    called = WORKFLOW[True]["workflow_call"]["inputs"]
    assert called["database_path"]["default"] == "auto" and called["resume_from"]["default"] == "start"
    deploy = yaml.safe_load((ROOT / ".github/workflows/deploy.yaml").read_text(encoding="utf-8"))
    dispatch = deploy[True]["workflow_dispatch"]["inputs"]
    assert dispatch["database_path"]["options"] == ["auto", "full"]
    assert dispatch["resume_from"]["options"] == ["start", "activation"]
    with_inputs = deploy["jobs"]["deploy"]["with"]
    assert "database_path" in with_inputs and "resume_from" in with_inputs


def test_the_update_runs_after_the_plan_before_vendor_work_and_without_stopping_applications() -> None:
    update = STEPS["Apply additive database update through PgBouncer"]
    assert "steps.database-chain.outputs.path == 'update'" in update["if"]
    order = [
        "Decide WC-124 database chain reuse",
        "Terraform dormant workload and migration dependency apply",
        "Preflight PgBouncer from private ACA environment",
        "Apply additive database update through PgBouncer",
        "Run vendor schema migrations against private PostgreSQL",
        "Verify migration evidence before application activation",
        "Activate runtime dependencies before application revisions",
    ]
    positions = [STEP_ORDER.index(name) for name in order]
    assert positions == sorted(positions)
    assert "--action Stop" not in update["run"] and "database-reset" not in update["run"]
    assert "wc177-restore-marker.json" in update["run"] and "wc177_database_update_job.py" in update["run"]
    assert (
        "--database-update wc177-database-update.json" in STEPS["Verify migration evidence before application activation"]["run"]
    )


def test_vendor_work_is_skipped_only_by_the_plan_proof_and_the_quiesce_follows_it() -> None:
    for name in (
        "Reclaim PostgreSQL connection budget before vendor migrations",
        "Run vendor schema migrations against private PostgreSQL",
        "Refresh Azure login before Temporal qualification",
        "Qualify exact Temporal startup through PgBouncer",
        "Refresh Keycloak replicas after realm import",
        "Quiesce running Demo applications before migrations",
    ):
        assert "steps.vendor-plan.outputs.vendor_reuse != 'true'" in STEPS[name]["if"], name
    assert (
        STEP_ORDER.index("Terraform dormant workload and migration dependency apply")
        < STEP_ORDER.index("Decide vendor migration and Temporal qualification reuse")
        < STEP_ORDER.index("Quiesce running Demo applications before migrations")
        < STEP_ORDER.index("Run vendor schema migrations against private PostgreSQL")
    )
    assert "continue-on-error" not in STEPS["Decide vendor migration and Temporal qualification reuse"]


def test_the_checkpoint_is_recorded_after_migration_acceptance_and_before_activation() -> None:
    persist = STEPS["Persist completed WC-124 database chain record"]
    assert persist["continue-on-error"] is True and "success()" in persist["if"]
    assert "--release-sha" in persist["run"] and "refresh" in persist["run"] and "create" in persist["run"]
    assert (
        STEP_ORDER.index("Verify migration evidence before application activation")
        < STEP_ORDER.index("Persist completed WC-124 database chain record")
        < STEP_ORDER.index("Activate runtime dependencies before application revisions")
    )


def test_stage_timings_are_recorded_and_uploaded_on_every_run() -> None:
    step = STEPS["Record WC-177 stage timings"]
    assert step["if"].startswith("always()") and step["continue-on-error"] is True
    assert STEP_ORDER.index("Record WC-177 stage timings") < STEP_ORDER.index("Upload plans and evidence")
    uploaded = STEPS["Upload plans and evidence"]["with"]["path"].split()
    for name in ("wc177-stage-timings.json", "wc177-database-update.json", "wc177-vendor-plan.json", "wc177-restore-marker.json"):
        assert name in uploaded


def test_release_qualification_is_off_by_default_with_a_founder_authority_record() -> None:
    template = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
    assert re.search(r"^\*\*Release Qualification:\*\* OFF$", template, re.M)
    assert re.search(r"^\*\*Release Qualification Authority:\*\* Founder standing instruction 2026-11-28", template, re.M)
    import prepare_pr_body

    assert prepare_pr_body.release_qualification_enabled(template) is False
    card = (ROOT / ".github/agent-context/office-platform-it-expert.md").read_text(encoding="utf-8")
    assert "Release Qualification Is Off By Default" in card


def test_documents_and_code_agree_on_the_names_of_the_update_path() -> None:
    names = ("database_path", "wc177-apply: update", "database_updater", "waooaw.wc143-database-chain-record/v2")
    assert "database_path" in WORKFLOW_TEXT and chain.RECORD_SCHEMA.endswith("/v2")
    documents = {
        "architecture/reference/agents/platform-it-expert-agent.md": names[:3],
        "architecture/reference/pipeline/azure-deployment-topology.md": names[:3],
        "architecture/reference/components/environment-readiness-and-data-continuity.md": ("database_updater",),
        "architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md": ("database_updater",),
        "architecture/reference/runbooks/demo-uat-persistent-state-lifecycle.md": ("database_path", "restore marker"),
    }
    for relative, tokens in documents.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for token in tokens:
            assert token in text, (relative, token)

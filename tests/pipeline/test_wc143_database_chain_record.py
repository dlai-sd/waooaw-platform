from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import wc143_database_chain_record as chain
from test_wc124_pre_activation_evidence import passing_identity, passing_temporal, succeeded
from wc124_pre_activation_evidence import validate_evidence

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
NOW = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
LIVE_FACTS = {
    "environment": "demo",
    "server": {"id": "/servers/psql", "created_at": "2026-01-01T00:00:00Z", "password_auth": "Enabled"},
    "credentials": [{"logical_secret_id": "db-app", "vault_secret_name": "db-app", "version_id": "v1"}],
}


def make_record(**overrides: object) -> dict:
    result = {
        **passing_identity("exec-1"),
        "schema": chain.PROVISIONER_RESULT_SCHEMA,
        "database_reset": None,
        "spend_authority": {"environment": "demo", "maximum_paise": 50000},
    }
    result.update(overrides)
    return chain.create_record(
        environment="demo",
        fingerprint="f" * 64,
        live_facts=copy.deepcopy(LIVE_FACTS),
        provisioner_result=result,
        provisioner_execution=succeeded("exec-1"),
        run_id="1",
        recorded_at=NOW - timedelta(days=1),
    )


def reject(record: dict, **overrides: object) -> str | None:
    arguments: dict = {
        "environment": "demo",
        "fingerprint": "f" * 64,
        "live_facts": copy.deepcopy(LIVE_FACTS),
        "now": NOW,
        "reset_requested": False,
        "transition_state": "REVOKED",
        "expected_spend_paise": 50000,
    }
    arguments.update(overrides)
    return chain.reject_reason(record, **arguments)


def seeded_repository(tmp_path: Path) -> Path:
    for name in chain.CHAIN_INPUTS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(name, encoding="utf-8")
    init = tmp_path / chain.INIT_DIRECTORY
    init.mkdir(parents=True)
    (init / "01.sql").write_text("select 1;", encoding="utf-8")
    return tmp_path


def test_unchanged_record_is_reusable() -> None:
    assert reject(make_record()) is None


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"reset_requested": True}, "reset requested"),
        ({"transition_state": "RECOVERY_HOLD"}, "transition state"),
        ({"fingerprint": "0" * 64}, "fingerprint changed"),
        ({"environment": "uat"}, "does not match"),
        ({"now": NOW + timedelta(days=7)}, "older than 7 days"),
        ({"now": NOW - timedelta(days=2)}, "future"),
        ({"expected_spend_paise": 100}, "spend authority"),
    ],
)
def test_any_changed_binding_selects_the_full_chain(overrides: dict, reason: str) -> None:
    assert reason in (reject(make_record(), **overrides) or "")


@pytest.mark.parametrize("fact", ["server", "credentials"])
def test_live_fact_drift_selects_the_full_chain(fact: str) -> None:
    drifted = copy.deepcopy(LIVE_FACTS)
    if fact == "server":
        drifted["server"]["id"] = "/servers/other"
    else:
        drifted["credentials"][0]["version_id"] = "v2"

    assert "live database" in (reject(make_record(), live_facts=drifted) or "")


def test_edited_record_fails_its_integrity_digest() -> None:
    record = make_record()
    record["provisioner_result"]["identity_schema"]["status"] = "passed "

    assert "integrity" in (reject(record) or "")


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"database_reset": {"status": "completed"}}, "database reset"),
        ({"mode": "canonical-url-refresh"}, "full provisioning"),
        ({"execution": "exec-2"}, "one execution"),
        ({"identity_schema": {"status": "failed"}}, "did not pass"),
    ],
)
def test_recorded_evidence_must_be_a_complete_unreset_provisioning(overrides: dict, reason: str) -> None:
    assert reason in (reject(make_record(**overrides)) or "")


def test_fingerprint_follows_inputs_and_rejects_unknown_environment(tmp_path: Path) -> None:
    root = seeded_repository(tmp_path)
    first = chain.chain_fingerprint(root, "demo", {"foundation_fingerprint": "a"})

    assert first == chain.chain_fingerprint(root, "demo", {"foundation_fingerprint": "a"})
    assert first != chain.chain_fingerprint(root, "demo", {"foundation_fingerprint": "b"})
    assert first != chain.chain_fingerprint(root, "uat", {"foundation_fingerprint": "a"})
    (root / chain.INIT_DIRECTORY / "01.sql").write_text("select 2;", encoding="utf-8")
    assert first != chain.chain_fingerprint(root, "demo", {"foundation_fingerprint": "a"})
    with pytest.raises(ValueError, match="demo or uat"):
        chain.chain_fingerprint(root, "prod")


def test_missing_chain_inputs_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing"):
        chain.chain_fingerprint(tmp_path, "demo")


def run_evaluate(tmp_path: Path, record: Path, **overrides: str) -> tuple[dict, subprocess.CompletedProcess[str]]:
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps(LIVE_FACTS), encoding="utf-8")
    transition = tmp_path / "transition.json"
    transition.write_text(json.dumps({"state": "REVOKED"}), encoding="utf-8")
    command = [
        sys.executable,
        str(ROOT / "scripts/wc143_database_chain_record.py"),
        "evaluate",
        "--record", str(record),
        "--environment", "demo",
        "--fingerprint", overrides.get("fingerprint", "f" * 64),
        "--live-facts", str(facts),
        "--transition", str(transition),
        "--reset-requested", "false",
        "--expected-spend-paise", "50000",
        "--output-directory", str(tmp_path),
    ]  # fmt: skip
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return json.loads(completed.stdout), completed


def test_reuse_restores_evidence_that_the_activation_gate_accepts(tmp_path: Path) -> None:
    record = chain.create_record(
        environment="demo",
        fingerprint="f" * 64,
        live_facts=LIVE_FACTS,
        provisioner_result={
            **passing_identity("exec-1"),
            "schema": chain.PROVISIONER_RESULT_SCHEMA,
            "database_reset": None,
            "spend_authority": {"environment": "demo", "maximum_paise": 50000},
        },
        provisioner_execution=succeeded("exec-1"),
        run_id="1",
        recorded_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record), encoding="utf-8")

    decision, completed = run_evaluate(tmp_path, path)

    assert completed.returncode == 0 and decision["reuse"] is True
    authority = json.loads((tmp_path / "wc124-reconciliation-authority.json").read_text())
    assert authority["status"] == "temporary-authority-revoked" and authority["reused_chain"] is True
    reuse = json.loads((tmp_path / "wc143-database-chain-reuse.json").read_text())
    accepted = validate_evidence(
        environment="demo",
        identity=json.loads((tmp_path / "wc124-db-provisioner-result.json").read_text()),
        identity_execution=json.loads((tmp_path / "wc124-db-provisioner-execution.json").read_text()),
        temporal=passing_temporal(),
        temporal_execution=succeeded("temporal-current"),
        chain_reuse=reuse,
    )
    assert accepted["identity_reused"] is True and accepted["identity_record_sha256"] == record["record_sha256"]
    with pytest.raises(ValueError, match="different identity execution"):
        validate_evidence(
            environment="demo",
            identity=passing_identity("exec-1"),
            identity_execution=succeeded("exec-1"),
            temporal=passing_temporal(),
            temporal_execution=succeeded("temporal-current"),
            chain_reuse={**reuse, "execution": "other"},
        )


def test_missing_corrupt_or_mismatched_record_selects_the_full_chain(tmp_path: Path) -> None:
    decision, completed = run_evaluate(tmp_path, tmp_path / "absent.json")
    assert completed.returncode == 0 and decision == {"reuse": False, "reason": "no record exists"}

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    decision, completed = run_evaluate(tmp_path, corrupt)
    assert completed.returncode == 0 and decision["reuse"] is False

    mismatched = tmp_path / "mismatched.json"
    mismatched.write_text(json.dumps(make_record()), encoding="utf-8")
    decision, _ = run_evaluate(tmp_path, mismatched, fingerprint="0" * 64)
    assert decision["reuse"] is False
    assert not (tmp_path / "wc124-db-provisioner-result.json").exists()


def step_block(name: str) -> str:
    start = WORKFLOW.index(f"      - name: {name}\n")
    following = re.search(r"\n      - (?:name|uses): ", WORKFLOW[start + 1 :])
    return WORKFLOW[start : start + 1 + following.start()] if following else WORKFLOW[start:]


@pytest.mark.parametrize(
    "name",
    [
        "Open bounded WC-124 schema reconciliation authority",
        "Grant bounded WC-124 reconciliation authority",
        "Quiesce Demo consumers before database reset",
        "Create WC-124 database provisioner",
        "Run WC-124 database provisioner",
    ],
)
def test_every_authority_chain_step_is_skipped_only_by_the_reuse_decision(name: str) -> None:
    assert "steps.database-chain.outputs.reuse != 'true'" in step_block(name)


def test_chain_decision_is_taken_before_any_authority_is_opened_and_record_is_fetched_first() -> None:
    order = [
        "Fetch recorded WC-143 database chain evidence",
        "Resolve WC-124 database transition state",
        "Resolve Plan B foundation mutation identity",
        "Decide WC-124 database chain reuse",
        "Open bounded WC-124 schema reconciliation authority",
    ]
    positions = [WORKFLOW.index(f"      - name: {name}\n") for name in order]
    assert positions == sorted(positions)
    assert "continue-on-error" not in step_block("Decide WC-124 database chain reuse")


def test_record_is_persisted_only_after_the_whole_job_succeeded_and_never_blocks_it() -> None:
    persist = step_block("Persist completed WC-124 database chain record")
    assert "success()" in persist and "continue-on-error: true" in persist
    assert "steps.database-chain.outputs.reuse != 'true'" in persist
    assert WORKFLOW.index("Persist completed WC-124 database chain record") < WORKFLOW.index("Upload plans and evidence")
    assert "wc143-database-chain-reuse.json" in step_block("Verify migration evidence before application activation")
    assert "Delete WC-124 database provisioner" in WORKFLOW[: WORKFLOW.index("Persist completed WC-124")]


def test_verification_and_terminal_cleanup_run_whether_or_not_the_chain_was_reused() -> None:
    for name in (
        "Verify WC-124 database credential handoff",
        "Ensure zero WC-124 database authority on terminal path",
        "Delete WC-124 database provisioner",
    ):
        assert "database-chain" not in step_block(name), name

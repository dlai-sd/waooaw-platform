from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml"
SOLUTION_PATH = ROOT / "architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md"
REQUIREMENTS_PATH = ROOT / "work-contracts/WC-120-requirements.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _operations(spec: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            if "operationId" in value:
                operations.append(value)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(spec["paths"])
    return operations


def test_wc120_public_contract_has_exact_candidate_operations_and_no_parallel_owner() -> None:
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    operations = _operations(spec)
    operation_ids = [operation["operationId"] for operation in operations]

    assert len(operations) == 17
    assert len(operation_ids) == len(set(operation_ids))
    assert spec["info"]["version"] == "1.0.0-candidate.2"
    assert set(spec["paths"]).issuperset(
        {
            "/api/v1/employment/relationships/{relationshipId}/conversation",
            "/api/v1/employment/relationships/{relationshipId}/conversation/contributions",
            "/api/v1/employment/relationships/{relationshipId}/conversation/events",
            "/api/v1/employment/relationships/{relationshipId}/conversation/handoffs",
            "/api/v1/employment/relationships/{relationshipId}/conversation/data-rights",
        }
    )
    assert all(
        path.startswith("/api/v1/employment/relationships/") or path == "/api/v1/channels/whatsapp/webhook"
        for path in spec["paths"]
    )


def test_wc120_external_schema_references_resolve_to_accepted_employment_contract() -> None:
    text = SPEC_PATH.read_text(encoding="utf-8")
    references = re.findall(r"\$ref:\s*['\"]?([^'\"\s]+)", text)
    external = [reference for reference in references if not reference.startswith("#")]
    assert external
    for reference in external:
        path, _, fragment = reference.partition("#")
        target = (SPEC_PATH.parent / path).resolve()
        assert target.is_file()
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
        current: Any = document
        for part in fragment.removeprefix("/").split("/"):
            if part:
                current = current[part.replace("~1", "/").replace("~0", "~")]
        assert current


def test_wc120_requirement_ledger_is_bound_to_current_solution_digest() -> None:
    ledger = yaml.safe_load(REQUIREMENTS_PATH.read_text(encoding="utf-8"))
    assert ledger["solution_digest"] == _sha256(SOLUTION_PATH)
    requirements = ledger["requirements"]
    assert len(requirements) == 44
    assert [entry["requirement_id"] for entry in requirements] == [f"WC120-R{number:03d}" for number in range(1, 45)]


def test_wc120_environment_manifests_validate_and_remain_default_off() -> None:
    directory = ROOT / "infrastructure/conversation-whatsapp"
    schema = json.loads((directory / "environment.schema.json").read_text(encoding="utf-8"))
    for environment in ("demo", "uat", "production"):
        manifest = json.loads((directory / f"{environment}.json").read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)
        assert manifest["environment"] == environment
        assert manifest["callbackAcceptanceEnabled"] is False
        assert manifest["dispatchEnabled"] is False
        assert manifest["providerEgressEnabled"] is False
        assert manifest["restoreRoutingEnabled"] is False


def test_wc120_backfill_is_bounded_restartable_and_marks_legacy_context_stale() -> None:
    sql = (ROOT / "infrastructure/postgres/operations/wc120-backfill.sql").read_text(encoding="utf-8")
    assert re.search(r"\bBETWEEN\s+1\s+AND\s+1000\b", sql, re.IGNORECASE)
    assert re.search(r"\bLIMIT\s+:'batch_size'", sql, re.IGNORECASE)
    assert "ORDER BY" in sql.upper()
    assert "conversation_migration_watermarks" in sql
    assert "legacy-unversioned" in sql
    assert "'freshness', 'STALE'" in sql
    assert "ON CONFLICT" in sql.upper()


def test_wc120_restore_verification_is_read_only_and_fails_on_invariant_breach() -> None:
    sql = (ROOT / "infrastructure/postgres/operations/wc120-restore-verification.sql").read_text(encoding="utf-8")
    assert not re.search(
        r"\b(INSERT|UPDATE|DELETE|TRUNCATE|ALTER|DROP|CREATE)\b",
        re.sub(r"--.*", "", sql),
        re.IGNORECASE,
    )
    assert "provider_event_claims" in sql
    assert "conversation_outbox" in sql
    assert "delivery_observations" in sql
    assert "1 / CASE" in sql


def test_wc120_rollback_fences_work_without_destroying_history_or_unknown_outcomes() -> None:
    sql = (ROOT / "infrastructure/postgres/operations/wc120-rollback.sql").read_text(encoding="utf-8")
    assert not re.search(r"\b(DELETE|TRUNCATE|DROP)\b", re.sub(r"--.*", "", sql), re.IGNORECASE)
    assert "PENDING" in sql
    assert "UNRESOLVED" in sql
    assert "DISPATCHING" in sql
    assert "reconcil" in sql.lower()

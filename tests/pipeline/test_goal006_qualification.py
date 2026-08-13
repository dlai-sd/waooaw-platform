from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from goal006_qualification import EXPECTED_FAMILIES, EXPECTED_TARGETS, validate_ledger

REPO_ROOT = Path(__file__).parents[2]
LEDGER_PATH = REPO_ROOT / "release/goal006/qualification-ledger.json"


def load_ledger() -> dict[str, Any]:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def assert_violation(ledger: dict[str, Any], code: str) -> None:
    assert code in validate_ledger(ledger, REPO_ROOT)


def test_complete_qualification_ledger_passes() -> None:
    assert validate_ledger(load_ledger(), REPO_ROOT) == []


def test_all_150_phase2_proofs_are_expected_collected_executed_and_passed() -> None:
    ledger = load_ledger()
    expected = sum(EXPECTED_FAMILIES.values())
    assert expected == 150
    assert {ledger["accounting"][field] for field in ("expected", "collected", "executed", "passed")} == {expected}
    assert ledger["accounting"]["omissions"] == []


@pytest.mark.parametrize("field", ["expected", "collected", "executed", "passed"])
def test_any_proof_count_mismatch_fails_qualification(field: str) -> None:
    ledger = load_ledger()
    ledger["accounting"][field] -= 1
    assert_violation(ledger, "PROOF_COUNT_MISMATCH")


def test_proof_identifier_commitment_detects_missing_or_renumbered_obligation() -> None:
    ledger = load_ledger()
    ledger["accounting"]["proof_ids_sha256"] = "0" * 64
    assert_violation(ledger, "PROOF_ID_ACCOUNTING_INVALID")


@pytest.mark.parametrize("status", ["PASS", "SKIPPED", "WAIVED", "NOT_APPLICABLE", "PENDING"])
def test_ct07_can_only_be_intentionally_allocated_to_phase3(status: str) -> None:
    ledger = load_ledger()
    ledger["ct_07"]["status"] = status
    assert_violation(ledger, "CT07_ALLOCATION_INVALID")


def test_ct07_is_not_in_phase2_executable_counts() -> None:
    ledger = load_ledger()
    assert ledger["ct_07"]["status"] == "NOT_EXECUTED_PHASE_3"
    assert "CT-07" not in EXPECTED_FAMILIES
    assert ledger["accounting"]["expected"] == 150


def test_every_proof_family_has_nonempty_existing_test_bindings() -> None:
    ledger = load_ledger()
    for family, expected_count in EXPECTED_FAMILIES.items():
        record = ledger["proof_families"][family]
        assert record["count"] == expected_count
        assert record["test_bindings"]
        assert all((REPO_ROOT / binding.split("::", 1)[0]).is_file() for binding in record["test_bindings"])


def test_missing_family_or_binding_fails_closed() -> None:
    ledger = load_ledger()
    del ledger["proof_families"]["SEC"]
    assert_violation(ledger, "PROOF_FAMILY_SET_INVALID")
    assert_violation(ledger, "SEC:ACCOUNTING_INVALID")


def test_all_evidence_contracts_are_collected() -> None:
    ledger = load_ledger()
    assert set(ledger["evidence_contracts"]) == {f"EVC-{number:02d}" for number in range(1, 9)}
    ledger["evidence_contracts"]["EVC-08"]["status"] = "MISSING"
    assert_violation(ledger, "EVIDENCE_CONTRACT_INCOMPLETE")


def test_target_classifications_are_preserved_without_accepting_recommendations() -> None:
    ledger = load_ledger()
    assert ledger["targets"] == EXPECTED_TARGETS
    ledger["targets"]["TGT-11"] = "ACCEPTED"
    assert_violation(ledger, "TARGET_CLASSIFICATION_INVALID")


def test_manifest_digest_runner_and_source_are_immutable_bindings() -> None:
    ledger = load_ledger()
    ledger["bindings"]["manifest_sha256"] = "0" * 64
    ledger["bindings"]["runner_digest"] = "latest"
    ledger["bindings"]["source_commit"] = "main"
    violations = validate_ledger(ledger, REPO_ROOT)
    assert "MANIFEST_BINDING_INVALID" in violations
    assert "RUNNER_BINDING_INVALID" in violations
    assert "SOURCE_COMMIT_BINDING_INVALID" in violations


def test_qualification_commands_are_docker_only() -> None:
    ledger = load_ledger()
    ledger["bindings"]["commands"].append("pytest tests")
    assert_violation(ledger, "NON_DOCKER_COMMAND")


def test_author_execution_is_not_independent_acceptance() -> None:
    ledger = copy.deepcopy(load_ledger())
    assert ledger["independence"]["acceptance_status"] == "DEFERRED_PENDING_INDEPENDENT_REVIEW"
    ledger["independence"]["qa_acceptor"] = ledger["independence"]["implementer"]
    assert_violation(ledger, "SELF_ACCEPTANCE_PROHIBITED")


def test_nonzero_test_accounting_must_match_complete_execution() -> None:
    ledger = load_ledger()
    ledger["accounting"]["test_passed"] -= 1
    assert_violation(ledger, "TEST_COUNT_MISMATCH")
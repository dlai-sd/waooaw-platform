from copy import deepcopy
from pathlib import Path

import yaml

from validate_requirement_ledger import (
    contract_requirement_ids,
    file_digest,
    validate_changed_ledgers,
    validate_ledger,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "work-contracts/WC-100-engineering-validation-efficiency.md"
LEDGER = ROOT / "work-contracts/WC-100-requirements.yaml"


def load_ledger() -> dict[str, object]:
    return yaml.safe_load(LEDGER.read_text(encoding="utf-8"))


def test_wc100_ledger_is_complete() -> None:
    requirement_ids = contract_requirement_ids(CONTRACT.read_text(encoding="utf-8"))

    assert requirement_ids == [f"WC100-R{number:03d}" for number in range(1, 31)]
    assert validate_ledger(load_ledger(), requirement_ids) == []


def test_preimplementation_gate_rejects_incomplete_ledger() -> None:
    ledger = load_ledger()
    rows = ledger["requirements"]
    assert isinstance(rows, list)
    rows[0] = {"requirement_id": "WC100-R001"}

    violations = validate_ledger(ledger, contract_requirement_ids(CONTRACT.read_text(encoding="utf-8")))

    assert any("FIELD_MISSING" in violation for violation in violations)


def test_duplicate_and_invalid_vocabulary_are_rejected() -> None:
    ledger = load_ledger()
    rows = ledger["requirements"]
    assert isinstance(rows, list)
    duplicate = deepcopy(rows[0])
    duplicate["initial_state"] = "maybe"
    rows.append(duplicate)

    violations = validate_ledger(ledger, contract_requirement_ids(CONTRACT.read_text(encoding="utf-8")))

    assert any("REQUIREMENT_DUPLICATE" in violation for violation in violations)
    assert any("INITIAL_STATE_INVALID" in violation for violation in violations)


def test_implementation_free_contract_can_be_not_applicable() -> None:
    ledger = {
        "schema": "waooaw.requirement-evidence-ledger/v1",
        "work_contract": "WC-EXAMPLE",
        "contract_path": "work-contracts/WC-EXAMPLE.md",
        "contract_status": "APPROVED",
        "implementation_scope": False,
        "result": "NOT_APPLICABLE",
        "not_applicable_reason": "Knowledge-only contract with no implementation obligations.",
        "requirements": [],
    }

    assert validate_ledger(ledger, []) == []


def test_done_rejects_unresolved_rows() -> None:
    ledger = load_ledger()
    ledger["result"] = "DONE"

    violations = validate_ledger(ledger, contract_requirement_ids(CONTRACT.read_text(encoding="utf-8")))

    assert any("DONE_UNRESOLVED" in violation for violation in violations)


def test_done_accepts_direct_evidence_and_exact_founder_reservation() -> None:
    ledger = load_ledger()
    ledger["result"] = "DONE"
    rows = ledger["requirements"]
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, dict)
        row["result"] = "PASS"
        row["evidence_refs"] = [f"test-results/wc100/{row['requirement_id']}.json"]
    rows[22]["result"] = "FOUNDER_RESERVED"
    rows[22]["evidence_refs"] = ["work-contracts/WC-100-engineering-validation-efficiency.md#83-advisory-first-rollout"]

    assert validate_ledger(ledger, contract_requirement_ids(CONTRACT.read_text(encoding="utf-8"))) == []


def test_contract_digest_change_invalidates_ledger() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")

    violations = validate_ledger(load_ledger(), contract_requirement_ids(contract), file_digest(contract + "changed"))

    assert violations == ["CONTRACT_STALE: ledger digest does not match the Work Contract"]


def test_changed_contract_requires_matching_ledger(tmp_path: Path) -> None:
    contracts = tmp_path / "work-contracts"
    contracts.mkdir()
    contract_path = contracts / "WC-200-example.md"
    contract_path.write_text("| WC200-R001 | Section 1 | obligation | test | PLANNED |\n", encoding="utf-8")

    violations = validate_changed_ledgers(tmp_path, ["work-contracts/WC-200-example.md"])

    assert violations == ["LEDGER_MISSING: work-contracts/WC-200-requirements.yaml"]

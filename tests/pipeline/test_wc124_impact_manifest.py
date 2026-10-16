"""WC-124 PST-WC01 current-state impact contract."""

# Implements: work-contracts/WC-124-demo-uat-persistent-state-lifecycle-implementation.md §PST-WC01
# Constitutional basis: C-023, C-059, C-080

from hashlib import sha256
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "work-contracts/WC-124-impact-manifest.yaml"


def load_manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def predicate_matches(path: Path, predicate: dict) -> bool:
    expected_exists = predicate.get("file_exists")
    if expected_exists is not None and path.exists() is not expected_exists:
        return False
    if not path.is_file():
        return expected_exists is False

    content = path.read_text(encoding="utf-8")
    return all(value in content for value in predicate.get("contains_all", [])) and all(
        value not in content for value in predicate.get("contains_none", [])
    )


def gap_ids() -> list[str]:
    return [gap["id"] for gap in load_manifest()["gaps"]]


def test_manifest_binds_the_exact_candidate_and_requirement() -> None:
    manifest = load_manifest()
    ledger_path = ROOT / manifest["requirement_binding"]["ledger"]
    ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))

    assert manifest["schema"] == "waooaw.wc124-impact-manifest/v1"
    assert manifest["work_contract"] == "WC-124"
    assert manifest["component"] == "PST-WC01"
    assert manifest["status"] == "LOCALLY_QUALIFIED_PROVIDER_GATES_RESERVED"
    assert manifest["requirement_binding"] == {
        "ledger": "work-contracts/WC-124-requirements.yaml",
        "requirements": ["WC124-R002"],
        "gaps": 13,
    }
    assert any(row["requirement_id"] == "WC124-R002" for row in ledger["requirements"])
    assert sha256((ROOT / "work-contracts/WC-124-persistent-state-inputs.yaml").read_bytes()).hexdigest() == (
        ledger["input_package_digest"]
    )


def test_all_declared_gaps_are_present_once_and_ordered() -> None:
    assert gap_ids() == [f"PST-{number:03d}" for number in range(1, 14)]


@pytest.mark.parametrize("gap_id", gap_ids())
def test_gap_baselines_and_target_oracles_are_exact(gap_id: str) -> None:
    gap = next(item for item in load_manifest()["gaps"] if item["id"] == gap_id)
    source = ROOT / gap["source"]

    assert gap["state"] in {
        "expected-fail",
        "authored-pending-qualification",
        "locally-qualified",
        "resolved",
    }
    assert gap["owning_surface"]
    assert gap["direct_evidence"].endswith(f"[{gap_id}]")

    if gap["state"] == "expected-fail":
        assert predicate_matches(source, gap["baseline"]), f"{gap_id} baseline no longer reproduces"
        assert not predicate_matches(source, gap["target"]), f"{gap_id} target now passes; mark it resolved"
    else:
        assert predicate_matches(source, gap["target"]), f"{gap_id} target oracle failed"

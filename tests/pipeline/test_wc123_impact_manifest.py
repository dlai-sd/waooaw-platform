"""WC-123 AUTH-WC-01 impact-manifest contract."""

# Implements: work-contracts/WC-123-authentication-authorization-implementation.md §7.1 AUTH-WC-01
# Constitutional basis: C-023, C-059, C-080

from hashlib import sha256
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "work-contracts/WC-123-impact-manifest.yaml"


def load_manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_accepted_source_digests_are_current() -> None:
    manifest = load_manifest()

    for relative_path, expected_digest in manifest["accepted_sources"].items():
        content = (ROOT / relative_path).read_bytes()
        assert sha256(content).hexdigest() == expected_digest


def test_all_requirements_and_components_are_bound() -> None:
    manifest = load_manifest()
    ledger = yaml.safe_load((ROOT / manifest["requirement_binding"]["ledger"]).read_text(encoding="utf-8"))
    requirement_ids = [row["requirement_id"] for row in ledger["requirements"]]

    assert requirement_ids == [f"WC123-R{number:03d}" for number in range(1, 49)]
    assert manifest["requirement_binding"]["count"] == len(requirement_ids)
    assert manifest["requirement_binding"]["components"] == [
        f"AUTH-WC-{number:02d}" for number in range(1, 8)
    ]


def test_legacy_authority_and_replacement_paths_are_explicit() -> None:
    manifest = load_manifest()
    authority = manifest["current_authority_paths"]

    assert authority["browser_session"]["legacy_creation"]
    assert authority["browser_session"]["removal_or_replacement"]
    assert authority["tenant_and_rls"]["legacy_acceptance"]
    assert authority["tenant_and_rls"]["removal_or_replacement"]
    assert authority["identity_provider"]["lifecycle_writer"]["role"] == "realm-management/manage-users"
    assert authority["identity_provider"]["lifecycle_writer"]["separation"]


def test_capacity_gap_fails_closed_before_auth_wc_02() -> None:
    manifest = load_manifest()
    capacity = manifest["capacity_and_timeout_budget"]

    assert manifest["status"] == "BLOCKED_CAPACITY_INPUTS"
    assert capacity["disposition"] == "BLOCKED"
    assert capacity["accepted_constraints"]["database_connection_ceiling_percent"] == 80
    assert capacity["missing_accepted_inputs"]
    assert "before AUTH-WC-02 starts" in capacity["unblocking_rule"]


def test_protected_actions_and_rollback_are_preserved() -> None:
    manifest = load_manifest()
    delivery = manifest["deployment_and_rollback"]

    assert "legacy browser tokens and claim authority remain rejected" in delivery["rollback"]
    assert set(delivery["protected_actions"]) == {
        "provider mutation",
        "cloud mutation",
        "deployment",
        "external traffic",
        "activation",
        "Production action",
        "approval",
        "merge",
    }

"""WC102 integrated qualification and rollback contracts."""

from pathlib import Path

import pytest
import yaml

from validation_control.qualification import build_qualification_manifest, build_rollback_manifest


ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "b" * 40
HEAD_SHA = "c" * 40


def load_catalog() -> dict[str, object]:
    return yaml.safe_load((ROOT / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))


def test_qualification_binds_clean_exact_head_and_full_inventory() -> None:
    catalog = load_catalog()

    manifest = build_qualification_manifest(catalog, base_sha=BASE_SHA, head_sha=HEAD_SHA, observed_head=HEAD_SHA, clean=True)

    assert manifest["required_gates"] == catalog["full_gates"]
    assert manifest["exact_head"] is True
    assert manifest["selective_enforcement"] is False


@pytest.mark.parametrize(
    ("observed_head", "clean", "message"),
    [("d" * 40, True, "QUALIFICATION_HEAD_MOVED"), (HEAD_SHA, False, "QUALIFICATION_WORKTREE_DIRTY")],
)
def test_qualification_rejects_moving_or_dirty_candidate(observed_head: str, clean: bool, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_qualification_manifest(
            load_catalog(), base_sha=BASE_SHA, head_sha=HEAD_SHA, observed_head=observed_head, clean=clean
        )


def test_rollback_restores_full_clean_inventory_and_discards_newer_evidence() -> None:
    catalog = load_catalog()

    rollback = build_rollback_manifest(catalog, incompatible_evidence_version=True)

    assert rollback["mode"] == "full-clean-qualification"
    assert rollback["required_gates"] == catalog["full_gates"]
    assert rollback["reuse_prior_results"] is False
    assert rollback["discard_incompatible_evidence"] is True

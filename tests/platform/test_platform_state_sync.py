"""Constitutional checks for canonical platform-state derivation."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "architecture/reference/platform-component-registry.yaml"
CATALOGUE = REPO_ROOT / "tests/constitutional/README.md"
ADDED_CCTS = {
    "CCT-BLUEPRINT-01": ["tests/platform/test_blueprint_ccts.py"],
    "CCT-TOKEN-HEALTH-01": ["tests/trust-layer/test_oauth_vault.py"],
    "CCT-TRIAL-01": ["tests/billing-engine/test_trial.py"],
    "CCT-TRIAL-02": ["tests/billing-engine/test_trial.py", "tests/ai-runtime/test_pse_router.py"],
    "CCT-COUPON-01": ["tests/billing-engine/test_promotions.py"],
    "CCT-REFERRAL-01": ["tests/billing-engine/test_promotions.py"],
    "CCT-ONBOARD-01": ["tests/billing-engine/test_payment.py"],
    "CCT-GRANDFATHER-01": ["tests/billing-engine/test_payment.py"],
    "CCT-WEBHOOK-01": ["tests/billing-engine/test_payment.py"],
    "CCT-PREPAID-01": ["tests/billing-engine/test_ccts.py"],
    "CCT-SELFAUDIT-01": ["tests/billing-engine/test_ccts.py", "tests/billing-engine/test_reconciliation_router.py"],
}


def test_current_summaries_match_canonical_registry() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/sync_platform_state.py", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_catalogue_count_matches_canonical_registry() -> None:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    text = CATALOGUE.read_text(encoding="utf-8")
    declarations = re.findall(
        r"(?:^\*\*|^## |^\| `)(CCT-[A-Z0-9]+(?:-[A-Z0-9]+)*)",
        text,
        flags=re.MULTILINE,
    )
    assert len(set(declarations)) == registry["cct_inventory"]["centrally_catalogued"]


def test_reconciled_ccts_have_executable_evidence() -> None:
    text = CATALOGUE.read_text(encoding="utf-8")
    for cct_id, paths in ADDED_CCTS.items():
        assert f"| `{cct_id}` |" in text
        for relative_path in paths:
            assert (REPO_ROOT / relative_path).is_file()
            assert cct_id in (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    assert "CCT-EF-03 — Reserved Evidence First extension" in text
    assert "SPECIFICATION GAP" in text


def test_corrected_billing_headers_reference_approved_specs() -> None:
    expected = {
        "src/billing-engine/wallet/models.py": (
            "architecture/reference/billing/wbe-component-spec.md",
            "## 3. Data Models",
        ),
        "src/billing-engine/skeleton/__init__.py": (
            "architecture/reference/components/manifest/wbe.yaml",
            "surface:",
        ),
    }
    for relative_path, (spec_path, section) in expected.items():
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert f"# Implements: {spec_path}" in source
        assert "# Constitutional basis: C-059" in source
        assert section in (REPO_ROOT / spec_path).read_text(encoding="utf-8")
"""Contracts for the GOAL-006 private runner image supply chain."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/goal006-runner-image.yaml").read_text(encoding="utf-8")


def test_runner_image_is_separate_from_exact_six_release() -> None:
    assert "goal006-private-runner" in WORKFLOW
    assert "goal006-exact-six-release" not in WORKFLOW
    assert "matrix.service" not in WORKFLOW


def test_runner_image_publishes_only_from_main_push() -> None:
    assert "push:" in WORKFLOW
    assert "branches: [main]" in WORKFLOW
    assert "push: ${{ github.event_name == 'push' }}" in WORKFLOW
    assert "load: ${{ github.event_name == 'pull_request' }}" in WORKFLOW


def test_runner_image_is_scanned_attested_and_digest_recorded() -> None:
    assert "aquasecurity/trivy-action@" in WORKFLOW
    assert "actions/attest-build-provenance@" in WORKFLOW
    assert "${{ steps.image.outputs.digest }}" in WORKFLOW
    assert "goal006-private-runner-${{ github.sha }}" in WORKFLOW


def test_runner_image_executes_qualification_contract_and_terraform_root() -> None:
    assert 'volume "$GITHUB_WORKSPACE:/workspace"' in WORKFLOW
    assert "python3 /workspace/scripts/goal006_runner_qualification.py --help" in WORKFLOW
    assert "az storage blob lease acquire --help" in WORKFLOW
    assert "az storage blob lease release --help" in WORKFLOW
    assert "terraform -chdir=/workspace/infrastructure/terraform/phase2/environments/demo/foundation init -backend=false" in WORKFLOW
    assert "terraform -chdir=/workspace/infrastructure/terraform/phase2/environments/demo/foundation validate" in WORKFLOW


def test_runner_image_executes_real_storage_lease_contract() -> None:
    assert "mcr.microsoft.com/azure-storage/azurite@sha256:" in WORKFLOW
    assert "from scripts.goal006_runner_qualification import acquire_blob_lease" in WORKFLOW
    assert "from scripts.goal006_runner_qualification import release_blob_lease" in WORKFLOW
    assert "--query properties.lease.status" in WORKFLOW
    assert 'test "$ready" = true' in WORKFLOW
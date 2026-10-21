"""Contracts for the GOAL-006 private runner image supply chain."""

from pathlib import Path

WORKFLOW = Path(".github/workflows/private-runner-image.yaml").read_text(encoding="utf-8")
DOCKERFILE = Path("infrastructure/runner/Dockerfile").read_text(encoding="utf-8")


def test_runner_image_is_separate_from_exact_six_release() -> None:
    assert "goal006-private-runner" in WORKFLOW
    assert "goal006-exact-six-release" not in WORKFLOW
    assert "matrix.service" not in WORKFLOW


def test_runner_image_workflow_qualifies_without_publishing() -> None:
    assert "push:\n    branches" not in WORKFLOW
    assert "pull_request:" in WORKFLOW
    assert "push: false" in WORKFLOW
    assert "load: true" in WORKFLOW
    assert "docker/login-action" not in WORKFLOW
    assert "attest-build-provenance" not in WORKFLOW
    assert "packages: write" not in WORKFLOW


def test_runner_image_is_scanned_for_fixable_os_vulnerabilities() -> None:
    assert "aquasecurity/trivy-action@" in WORKFLOW
    assert "exit-code: 1" in WORKFLOW


def test_runner_image_retries_transient_apt_download_failures() -> None:
    assert "ARG APT_ACQUIRE_RETRIES=5" in DOCKERFILE
    assert DOCKERFILE.count('-o Acquire::Retries="${APT_ACQUIRE_RETRIES}"') == 4


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
    assert "from scripts.goal006_runner_qualification import reconcile_stale_probe_blobs" in WORKFLOW
    assert "goal006/demo/qualification/goal006-demo-123-1.json" in WORKFLOW
    assert "assert deleted ==" in WORKFLOW
    assert WORKFLOW.count("az storage blob exists") == 2
    assert "--query properties.lease.status" in WORKFLOW
    assert 'test "$ready" = true' in WORKFLOW
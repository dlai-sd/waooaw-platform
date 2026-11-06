"""Contracts for the GOAL-006 private runner image supply chain."""

import json
from pathlib import Path

WORKFLOW = Path(".github/workflows/private-runner-image.yaml").read_text(encoding="utf-8")
DOCKERFILE = Path("infrastructure/runner/Dockerfile").read_text(encoding="utf-8")


def test_runner_base_pins_supported_release_and_qualification_checks_same_version() -> None:
    assert DOCKERFILE.splitlines()[0] == (
        "FROM ghcr.io/actions/actions-runner@sha256:759a1d94a15b05941aba5196974ff43fe15b4cbba29b694b35cbc32a1166b232"
    )
    assert 'set -euo pipefail\n            /home/runner/bin/Runner.Listener --version | grep -Fxq "2.338.2"' in WORKFLOW
    assert "2.336.0" not in WORKFLOW


def test_environment_pins_adopt_verified_main_runner_publication() -> None:
    image = "ghcr.io/dlai-sd/goal006-private-runner@sha256:371007f6247abd2e21bbd98c8c7d46c4faed80147ad5455c5c5ddbff78d494c6"
    stack = Path("infrastructure/deployment-stacks/goal006-runner")
    for environment in ("demo", "uat", "prod"):
        parameters = json.loads((stack / f"{environment}.parameters.json").read_text(encoding="utf-8"))
        assert parameters["parameters"]["runnerImage"]["value"] == image


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
    remove_ppa = "rm -f /etc/apt/sources.list.d/git-core-ubuntu-ppa-noble.sources"
    assert remove_ppa in DOCKERFILE
    assert DOCKERFILE.index(remove_ppa) < DOCKERFILE.index("apt-get -o Acquire::Retries")


def test_runner_image_executes_qualification_contract_and_terraform_root() -> None:
    assert 'volume "$GITHUB_WORKSPACE:/workspace"' in WORKFLOW
    assert "python3 /workspace/scripts/goal006_runner_qualification.py --help" in WORKFLOW
    assert "az storage blob lease acquire --help" in WORKFLOW
    assert "az storage blob lease release --help" in WORKFLOW
    assert (
        "terraform -chdir=/workspace/infrastructure/terraform/phase2/environments/demo/foundation init -backend=false" in WORKFLOW
    )
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

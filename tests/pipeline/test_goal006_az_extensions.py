from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/goal006_az_extensions.sh"
WORKFLOW = ROOT / ".github/workflows/environment-deployment.yaml"
DOCKERFILE = ROOT / "infrastructure/runner/Dockerfile"

FAKE_AZ = """#!/usr/bin/env bash
echo "$*" >> "$AZ_CALLS"
case "$1 $2" in
  "extension show")
    name=$4
    [ -f "$AZ_STATE/$name" ] || exit 3
    case "$6" in version) cat "$AZ_STATE/$name" ;; path) echo "$AZ_STATE/ext-$name" ;; esac
    ;;
  "extension add")
    name=$4 version=$6
    count_file="$AZ_STATE/$name.attempts"
    count=$(( $(cat "$count_file" 2>/dev/null || echo 0) + 1 ))
    echo "$count" > "$count_file"
    [ "$count" -gt "${AZ_FAIL_ADDS:-0}" ] || exit 1
    echo "$version" > "$AZ_STATE/$name"
    ;;
  *) [ -f "$AZ_STATE/containerapp" ] && [ -f "$AZ_STATE/log-analytics" ] || exit 2 ;;
esac
"""


def pins() -> dict[str, str]:
    text = DOCKERFILE.read_text(encoding="utf-8")
    return {
        "containerapp": re.search(r"^ARG AZ_CONTAINERAPP_EXTENSION_VERSION=(\S+)$", text, re.M).group(1),
        "log-analytics": re.search(r"^ARG AZ_LOG_ANALYTICS_EXTENSION_VERSION=(\S+)$", text, re.M).group(1),
    }


def run(tmp_path: Path, fail_adds: int = 0, preinstalled: dict[str, str] | None = None, dockerfile: Path = DOCKERFILE):
    bin_dir, state = tmp_path / "bin", tmp_path / "state"
    bin_dir.mkdir()
    state.mkdir(exist_ok=True)
    (bin_dir / "az").write_text(FAKE_AZ, encoding="utf-8")
    (bin_dir / "az").chmod(0o755)
    for name, version in (preinstalled or {}).items():
        (state / name).write_text(version, encoding="utf-8")
    calls = tmp_path / "calls"
    calls.touch()
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "AZ_CALLS": str(calls),
        "AZ_STATE": str(state),
        "AZ_FAIL_ADDS": str(fail_adds),
        "GOAL006_RUNNER_DOCKERFILE": str(dockerfile),
        "GOAL006_AZ_EXTENSION_RETRY_SECONDS": "0",
    }
    result = subprocess.run(["bash", str(SCRIPT)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    return result, calls.read_text(encoding="utf-8").splitlines()


def test_installs_the_dockerfile_pins_when_the_runner_image_lacks_them(tmp_path: Path) -> None:
    result, calls = run(tmp_path)
    assert result.returncode == 0, result.stderr
    for name, version in pins().items():
        assert f"extension add --name {name} --version {version} --upgrade --yes --only-show-errors" in calls
    assert "containerapp job logs show --help" in calls
    assert "monitor log-analytics query --help" in calls
    assert "status=ready" in result.stdout


def test_skips_install_when_pinned_versions_are_already_present(tmp_path: Path) -> None:
    result, calls = run(tmp_path, preinstalled=pins())
    assert result.returncode == 0, result.stderr
    assert not [call for call in calls if call.startswith("extension add")]
    assert result.stdout.count("status=present") == 2


def test_recognises_wheels_that_only_record_their_version_in_dist_info(tmp_path: Path) -> None:
    version = pins()["log-analytics"]
    dist_info = tmp_path / "state" / "ext-log-analytics" / f"log_analytics-{version}.dist-info"
    dist_info.mkdir(parents=True)
    result, calls = run(tmp_path, preinstalled={"containerapp": pins()["containerapp"], "log-analytics": "None"})
    assert result.returncode == 0, result.stderr
    assert not [call for call in calls if call.startswith("extension add")]


def test_retries_transient_install_failures(tmp_path: Path) -> None:
    result, calls = run(tmp_path, fail_adds=2)
    assert result.returncode == 0, result.stderr
    assert len([call for call in calls if call.startswith("extension add --name containerapp")]) == 3
    assert "status=retry attempt=2/4" in result.stdout


def test_fails_loudly_when_the_extension_cannot_be_installed(tmp_path: Path) -> None:
    result, calls = run(tmp_path, fail_adds=99)
    assert result.returncode == 1
    assert "::error title=Azure CLI extension install failed::containerapp" in result.stderr
    assert len([call for call in calls if call.startswith("extension add")]) == 4
    assert not [call for call in calls if "logs show" in call]


def test_fails_when_a_pin_is_missing(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("ARG AZ_CONTAINERAPP_EXTENSION_VERSION=1.2.0b5\n", encoding="utf-8")
    result, _ = run(tmp_path, dockerfile=dockerfile)
    assert result.returncode == 1
    assert "AZ_LOG_ANALYTICS_EXTENSION_VERSION is not declared" in result.stderr


def test_private_runner_job_installs_extensions_before_any_azure_cli_use() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    job = workflow[workflow.index("\n  terraform:\n") : workflow.index("\n  cleanup-private:\n")]
    install = job.index("- name: Install pinned Azure CLI extensions\n        run: bash scripts/goal006_az_extensions.sh")
    assert install < job.index("uses: azure/login@")
    assert install < job.index("az containerapp job logs show")


@pytest.mark.parametrize("job_name", ["start-broker", "cleanup-private"])
def test_hosted_jobs_install_pins_before_login_and_queries(job_name: str) -> None:
    job = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"][job_name]
    assert job["runs-on"] == "ubuntu-latest"
    steps = job["steps"]
    install = next(index for index, step in enumerate(steps) if step.get("run") == "bash scripts/goal006_az_extensions.sh")
    login = next(index for index, step in enumerate(steps) if step.get("uses", "").startswith("azure/login@"))
    assert install < login
    assert all("az " not in step.get("run", "") for step in steps[:install])


def test_provisioner_reports_a_missing_result_instead_of_a_bare_jq_exit() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    capture = workflow.index("> wc124-db-provisioner-result.json\n")
    guard = workflow.index("if [ ! -s wc124-db-provisioner-result.json ]; then", capture)
    assert guard < workflow.index('jq --arg execution "$execution_name"', capture)
    assert "::error title=WC-124 provisioner result missing::" in workflow[guard : guard + 400]

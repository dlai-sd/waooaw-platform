"""WC-128 contracts: broker and cleanup control image resolve from the runner-stack ACR with GHCR fallback."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import goal006_runner_image_source as source

ROOT = Path(__file__).resolve().parents[2]
STACK = ROOT / "infrastructure/deployment-stacks/goal006-runner"
MAIN_BICEP = (STACK / "main.bicep").read_text(encoding="utf-8")
SUBSCRIPTION_BICEP = (STACK / "subscription.bicep").read_text(encoding="utf-8")
ENVIRONMENT = yaml.safe_load((ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8"))

SERVER = "acrwaooawrundemo2ed118.azurecr.io"
BLUEPRINT = "ghcr.io/dlai-sd/goal006-private-runner@sha256:" + "a" * 64
CHILD = "sha256:" + "c" * 64
PULL_ID = (
    "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/resourceGroups/waooaw-demo-runner-rg/providers/"
    "Microsoft.ManagedIdentity/userAssignedIdentities/goal006-demo-runner-image-pull-identity"
)
INDEX = {"mediaType": "application/vnd.oci.image.index.v1+json", "manifests": [{"digest": CHILD}]}


def job(server: str = SERVER, identity: str = PULL_ID, attached: bool = True) -> dict[str, Any]:
    identities = {"/subscriptions/x/providers/Microsoft.ManagedIdentity/userAssignedIdentities/broker": {}}
    if attached:
        identities[identity] = {}
    return {
        "identity": {"userAssignedIdentities": identities},
        "properties": {"configuration": {"registries": [{"server": server, "identity": identity}]}},
    }


class FakeAcr:
    def __init__(self, *, present: bool = False, create_fails: bool = False) -> None:
        self.manifests: dict[str, dict[str, Any]] = {}
        self.create_fails = create_fails
        self.calls: list[list[str]] = []
        if present:
            self._seed()

    def _seed(self) -> None:
        base = f"{SERVER}/dlai-sd/goal006-private-runner"
        self.manifests[f"{base}@sha256:{'a' * 64}"] = INDEX
        self.manifests[f"{base}@{CHILD}"] = {"mediaType": "application/vnd.oci.image.manifest.v1+json"}

    def __call__(self, arguments: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        arguments = list(arguments)
        self.calls.append(arguments)
        if arguments[:4] == ["docker", "buildx", "imagetools", "inspect"]:
            manifest = self.manifests.get(arguments[-1])
            if manifest is None:
                return subprocess.CompletedProcess(arguments, 1, "", "not found")
            return subprocess.CompletedProcess(arguments, 0, json.dumps(manifest), "")
        if arguments[:4] == ["docker", "buildx", "imagetools", "create"]:
            if self.create_fails:
                return subprocess.CompletedProcess(arguments, 1, "", "unauthorized")
            self._seed()
            return subprocess.CompletedProcess(arguments, 0, "", "")
        raise AssertionError(arguments)


def resolve(mode: str, run: FakeAcr, **overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "mode": mode,
        "blueprint_image": BLUEPRINT,
        "login_server": SERVER,
        "job": job(),
        "registry_ready": True,
        "run": run,
        "sleep": lambda _seconds: None,
    }
    values.update(overrides)
    return source.resolve_control_image(**values)


def test_publish_copies_missing_digest_and_selects_runner_acr() -> None:
    registry = FakeAcr()
    evidence = resolve("publish", registry)
    assert evidence["source"] == "runner-acr"
    assert evidence["copied"] is True
    assert evidence["control_image"] == f"{SERVER}/dlai-sd/goal006-private-runner@sha256:{'a' * 64}"
    assert evidence["fallback_reason"] == ""


def test_publish_reuses_present_digest_without_copy() -> None:
    registry = FakeAcr(present=True)
    evidence = resolve("publish", registry)
    assert evidence["source"] == "runner-acr"
    assert evidence["copied"] is False
    assert not any(call[3] == "create" for call in registry.calls)


def test_verify_never_copies_and_falls_back_when_absent() -> None:
    registry = FakeAcr()
    evidence = resolve("verify", registry)
    assert evidence["control_image"] == BLUEPRINT
    assert evidence["source"] == "ghcr"
    assert "not present" in evidence["fallback_reason"]
    assert not any(call[3] == "create" for call in registry.calls)
    assert resolve("verify", FakeAcr(present=True))["source"] == "runner-acr"


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"registry_ready": False}, "not reachable"),
        ({"login_server": "acrwaooawdemo2ed118.azurecr.io"}, "runner-stack WAOOAW ACR"),
        ({"job": job(server="other.azurecr.io")}, "does not declare"),
        ({"job": job(attached=False)}, "does not declare"),
        ({"job": job(identity=PULL_ID.replace("image-pull", "broker"))}, "does not declare"),
        ({"job": {"properties": {}}}, "does not declare"),
    ],
)
def test_unusable_registry_or_job_falls_back_to_ghcr(overrides: dict[str, Any], reason: str) -> None:
    registry = FakeAcr(present=True)
    evidence = resolve("publish", registry, **overrides)
    assert evidence["control_image"] == BLUEPRINT
    assert evidence["source"] == "ghcr"
    assert reason in evidence["fallback_reason"]


def test_copy_failure_falls_back_to_ghcr() -> None:
    evidence = resolve("publish", FakeAcr(create_fails=True))
    assert evidence["control_image"] == BLUEPRINT
    assert "could not be mirrored" in evidence["fallback_reason"]


def test_mutable_blueprint_is_rejected() -> None:
    with pytest.raises(ValueError, match="immutable GHCR digest"):
        resolve("publish", FakeAcr(), blueprint_image="ghcr.io/dlai-sd/goal006-private-runner:latest")


def test_cli_writes_evidence_and_prints_control_image(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job()), encoding="utf-8")
    output = tmp_path / "evidence.json"
    monkeypatch.setattr(source, "resolve_control_image", lambda **kwargs: {"control_image": BLUEPRINT, **kwargs["job"]})
    assert (
        source.main(
            [
                "--mode",
                "verify",
                "--blueprint-image",
                BLUEPRINT,
                "--login-server",
                SERVER.upper(),
                "--job",
                str(job_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.strip() == BLUEPRINT
    assert json.loads(output.read_text(encoding="utf-8"))["control_image"] == BLUEPRINT


def test_runner_stack_declares_registry_pull_identity_and_least_privilege_roles() -> None:
    assert "var runnerRegistryName = 'acrwaooawrun${environment}${substring(subscription().subscriptionId, 0, 6)}'" in MAIN_BICEP
    assert "adminUserEnabled: false" in MAIN_BICEP
    assert re.search(r"name: 'Basic'", MAIN_BICEP)
    assert "imagePublisherPrincipalId: bootstrapPrincipalId" in SUBSCRIPTION_BICEP
    for role in ("7f951dda-4ed3-4680-a7ca-43fe172d538d", "8311e382-0749-4cb8-b61a-304f252e45ec"):
        assert role in MAIN_BICEP
    for resource in ("runnerJob", "brokerJob", "cleanupBrokerJob"):
        block = MAIN_BICEP.split(f"resource {resource} 'Microsoft.App/jobs@2024-03-01'", 1)[1].split("\nresource ", 1)[0]
        assert "registries: runnerRegistries" in block
        assert "'${imagePullIdentity.id}': {}" in block
        assert "image: runnerImage" in block
    reconciler = MAIN_BICEP.split("resource reconcilerJob", 1)[1].split("\nresource ", 1)[0]
    assert "registries" not in reconciler


def _step(job_name: str, step_name: str) -> dict[str, Any]:
    return next(step for step in ENVIRONMENT["jobs"][job_name]["steps"] if step.get("name") == step_name)


@pytest.mark.parametrize(
    ("step_name", "mode", "job_file"),
    [
        ("Start private signing broker", "publish", "broker-job.json"),
        ("Start private cleanup broker", "verify", "cleanup-job.json"),
    ],
)
def test_workflow_resolves_control_image_with_ghcr_fallback(step_name: str, mode: str, job_file: str) -> None:
    job_name = next(
        name for name, value in ENVIRONMENT["jobs"].items() if any(step.get("name") == step_name for step in value["steps"])
    )
    step = _step(job_name, step_name)
    script = step["run"]
    assert step["env"]["TARGET_ENVIRONMENT"] == "${{ inputs.environment }}"
    assert 'runner_registry="acrwaooawrun${TARGET_ENVIRONMENT}${subscription_compact:0:6}"' in script
    assert f"--mode {mode}" in script
    assert f"--job {job_file}" in script
    assert '|| execution_control_image="$blueprint_runner_image"' in script
    assert 'execution_runner_image="$blueprint_runner_image"' in script
    assert '--expected-image "$blueprint_runner_image"' in script
    assert script.index(f"> {job_file}") < script.index("goal006_runner_image_source.py")
    assert script.index("goal006_runner_image_source.py") < script.index("goal006_runner_execution.py")

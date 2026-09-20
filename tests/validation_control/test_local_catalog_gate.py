"""Behavior contracts for local WC-104 catalog execution."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from validation_control import local_catalog_gate


IDENTITY = "sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64


def specification() -> dict[str, object]:
    return {
        "runner_id": "python",
        "dockerfile": "Dockerfile",
        "identity": IDENTITY,
        "identity_inputs": {"platform": "linux/amd64", "context_manifest": {}},
    }


def test_local_fallback_builds_once_then_reuses_identity_image(monkeypatch, tmp_path: Path) -> None:
    inspected = iter((None, IMAGE_ID, IMAGE_ID))
    builds: list[list[str]] = []
    runner_digest = "sha256:" + "c" * 64
    monkeypatch.setattr(local_catalog_gate, "image_id", lambda image, repository: next(inspected))
    monkeypatch.setattr(local_catalog_gate, "create_context", lambda repository, context, spec: context.mkdir(parents=True))

    def build(command: list[str], **unused: object) -> SimpleNamespace:
        builds.append(command)
        metadata = Path(command[command.index("--metadata-file") + 1])
        metadata.write_text(json.dumps({"containerimage.digest": runner_digest}), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        build,
    )

    first = local_catalog_gate.local_fallback_runner(tmp_path, "python", specification())
    second = local_catalog_gate.local_fallback_runner(tmp_path, "python", specification())

    assert first[1:] == (IMAGE_ID, runner_digest, 1)
    assert second[1:] == (IMAGE_ID, runner_digest, 0)
    assert len(builds) == 1
    assert builds[0][0].endswith("docker")
    assert builds[0][1:3] == ["buildx", "build"]
    assert builds[0][builds[0].index("--platform") + 1] == "linux/amd64"


def test_untrusted_manifest_is_a_miss_without_pull(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "test-results/wc104/runner-manifests/python.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"schema": "untrusted"}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_REPOSITORY", "dlai-sd/waooaw")
    monkeypatch.setattr(local_catalog_gate.shutil, "which", lambda executable: f"/usr/bin/{executable}")
    commands: list[list[str]] = []
    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        lambda command, **unused: commands.append(command) or SimpleNamespace(returncode=0),
    )

    assert local_catalog_gate.trusted_runner(tmp_path, "python", specification()) is None
    assert commands == []


def test_host_gate_executes_plan_without_resolving_runner(monkeypatch, tmp_path: Path) -> None:
    catalog = {
        "schema": "waooaw.validation-catalog/v1",
        "version": "test",
        "runners": {"python": {"compose_service": "runner", "profile": "test"}},
        "commands": {"host": {"shell": "true", "execution": "host", "runner_required": False}},
        "gates": {
            "host": {
                "runner_id": "python",
                "command_id": "host",
                "resources": {},
                "retry_policy": "none",
                "artifacts": {},
            }
        },
    }
    validation = tmp_path / "validation"
    validation.mkdir()
    (validation / "engineering-validation.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    executor = tmp_path / "scripts/validation_control/catalog_execution.py"
    executor.parent.mkdir(parents=True)
    executor.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        local_catalog_gate,
        "load_supply_config",
        lambda unused: pytest.fail("host execution resolved a validation runner"),
    )
    captured: list[list[str]] = []
    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        lambda command, **unused: captured.append(command) or SimpleNamespace(returncode=0),
    )

    assert local_catalog_gate.execute_gate(tmp_path, "host", "a" * 40, "b" * 40, tmp_path) == 0
    assert "--image-id" not in captured[0]
    plan = json.loads((tmp_path / "test-results/wc104/local-plans/host.json").read_text(encoding="utf-8"))
    assert plan["nodes"][0]["command"] == "true"


def test_gate_identity_hashes_only_declared_environment(monkeypatch, tmp_path: Path) -> None:
    tool_digest = "sha256:" + "d" * 64
    catalog = {
        "schema": "waooaw.validation-catalog/v1",
        "version": "test-v1",
        "runners": {"python": {"compose_service": "runner", "profile": "test"}},
        "commands": {
            "host": {
                "shell": "true",
                "execution": "host",
                "runner_required": False,
                "tool_digest": tool_digest,
            }
        },
        "gates": {
            "host": {
                "runner_id": "python",
                "command_id": "host",
                "resources": {},
                "retry_policy": "none",
                "artifacts": {},
                "environment": ["DECLARED"],
            }
        },
    }
    validation = tmp_path / "validation"
    validation.mkdir()
    (validation / "engineering-validation.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    monkeypatch.setenv("DECLARED", "first")
    monkeypatch.setenv("UNDECLARED", "first")
    original = local_catalog_gate.gate_execution_identity(tmp_path, "host", "a" * 40)

    monkeypatch.setenv("UNDECLARED", "second")
    undeclared_changed = local_catalog_gate.gate_execution_identity(tmp_path, "host", "a" * 40)
    monkeypatch.setenv("DECLARED", "second")
    declared_changed = local_catalog_gate.gate_execution_identity(tmp_path, "host", "a" * 40)

    assert original["runner_digest"] == tool_digest
    assert undeclared_changed["environment_digest"] == original["environment_digest"]
    assert declared_changed["environment_digest"] != original["environment_digest"]


def test_runner_backed_execution_requires_exact_image_and_disables_pull() -> None:
    source = (Path(__file__).resolve().parents[2] / "scripts/validation_control/catalog_execution.py").read_text(encoding="utf-8")

    assert '"--pull",\n        "never"' in source
    assert 'raise ValueError("--image-id is required for runner-backed catalog execution")' in source
